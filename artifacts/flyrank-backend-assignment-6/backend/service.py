"""Classification orchestration: kill switch, cache, retries, repair and observability."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from .models import ClassificationResult, OperationalMetadata
from .prompts import PROMPT_VERSION
from .providers import Provider, ProviderFailure, ProviderOutputError, ProviderResponse
from .quarantine import QuarantineSink
from .settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    response: ProviderResponse
    expires_at: float


class ClassifierService:
    def __init__(
        self,
        settings: Settings,
        provider: Provider,
        sleep=asyncio.sleep,
        clock=time.monotonic,
        quarantine: QuarantineSink | None = None,
        jitter_fn: Callable[[float, float], float] = random.uniform,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self._sleep = sleep
        self._clock = clock
        self._cache: dict[str, _CacheEntry] = {}
        self._quarantine = quarantine or QuarantineSink(settings.quarantine_path)
        self._jitter = jitter_fn

    async def classify(self, text: str) -> ClassificationResult:
        if not self.settings.llm_enabled:
            raise ProviderFailure("disabled")

        started = self._clock()
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cached = self._cache.get(key)
        if cached and cached.expires_at > started:
            return self._result(
                cached.response,
                started,
                cache_hit=True,
                retries=0,
                repair_count=0,
            )
        if cached:
            self._cache.pop(key, None)

        repair_count = 0
        total_retries = 0
        try:
            response, retries = await self._call_with_retries(
                self.provider.classify,
                text,
            )
            total_retries += retries
        except ProviderOutputError as first_error:
            repair_count = 1
            self._quarantine.record(
                text=text,
                raw_output=first_error.raw_output,
                validation_error=first_error.validation_error,
                attempt=1,
                prompt_version=PROMPT_VERSION,
            )

            async def repair(value: str) -> ProviderResponse:
                return await self.provider.repair(
                    value,
                    first_error.validation_error,
                )

            try:
                response, retries = await self._call_with_retries(repair, text)
                total_retries += retries
            except ProviderOutputError as final_error:
                self._quarantine.record(
                    text=text,
                    raw_output=final_error.raw_output,
                    validation_error=final_error.validation_error,
                    attempt=2,
                    prompt_version=PROMPT_VERSION,
                )
                raise

        if self.settings.cache_ttl_seconds:
            self._cache[key] = _CacheEntry(
                response=response,
                expires_at=self._clock() + self.settings.cache_ttl_seconds,
            )
        return self._result(
            response,
            started,
            cache_hit=False,
            retries=total_retries,
            repair_count=repair_count,
        )

    async def _call_with_retries(
        self,
        operation: Callable[[str], Awaitable[ProviderResponse]],
        text: str,
    ) -> tuple[ProviderResponse, int]:
        for attempt in range(self.settings.max_retries + 1):
            try:
                return await operation(text), attempt
            except ProviderOutputError:
                raise
            except ProviderFailure as exc:
                if not self._is_retryable(exc) or attempt == self.settings.max_retries:
                    raise
                base_delay = min(
                    self.settings.retry_backoff_seconds * (2**attempt),
                    2.0,
                )
                jitter = (
                    self._jitter(0.0, min(base_delay * 0.25, 0.5))
                    if base_delay > 0
                    else 0.0
                )
                delay = base_delay + jitter
                if exc.retry_after_seconds is not None:
                    delay = max(delay, exc.retry_after_seconds)
                await self._sleep(delay)
        raise RuntimeError("unreachable")

    @staticmethod
    def _is_retryable(error: ProviderFailure) -> bool:
        return error.kind in {"timeout", "rate_limited", "upstream"}

    def _estimated_cost(self, response: ProviderResponse) -> float | None:
        if response.input_tokens is None or response.output_tokens is None:
            return None
        cost = (
            response.input_tokens * self.settings.input_cost_per_million_usd
            + response.output_tokens * self.settings.output_cost_per_million_usd
        ) / 1_000_000
        return round(cost, 8)

    def _result(
        self,
        response: ProviderResponse,
        started: float,
        *,
        cache_hit: bool,
        retries: int,
        repair_count: int,
    ) -> ClassificationResult:
        duration_ms = round((self._clock() - started) * 1000, 2)
        estimated_cost = self._estimated_cost(response)
        metadata = OperationalMetadata(
            provider=self.provider.name,
            model=self.provider.model,
            prompt_version=PROMPT_VERSION,
            duration_ms=duration_ms,
            cache_hit=cache_hit,
            retries=retries,
            repair_attempted=repair_count > 0,
            repair_count=repair_count,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            estimated_cost_usd=estimated_cost,
        )
        logger.info(
            "llm_classification provider=%s model=%s prompt_version=%s duration_ms=%s cache_hit=%s retries=%s repair_count=%s input_tokens=%s output_tokens=%s estimated_cost_usd=%s",
            metadata.provider,
            metadata.model,
            metadata.prompt_version,
            metadata.duration_ms,
            metadata.cache_hit,
            metadata.retries,
            metadata.repair_count,
            metadata.input_tokens,
            metadata.output_tokens,
            metadata.estimated_cost_usd,
        )
        return ClassificationResult(
            **response.classification.model_dump(),
            metadata=metadata,
        )
