"""Classification orchestration: kill switch, cache, retries, and observability."""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass

from .models import ClassificationResult, OperationalMetadata
from .providers import Provider, ProviderFailure, ProviderOutputError, ProviderResponse
from .settings import Settings


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
    ) -> None:
        self.settings = settings
        self.provider = provider
        self._sleep = sleep
        self._clock = clock
        self._cache: dict[str, _CacheEntry] = {}

    async def classify(self, text: str) -> ClassificationResult:
        if not self.settings.llm_enabled:
            raise ProviderFailure("disabled")

        started = self._clock()
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cached = self._cache.get(key)
        if cached and cached.expires_at > started:
            return self._result(cached.response, started, cache_hit=True, retries=0)
        if cached:
            self._cache.pop(key, None)

        response, retries = await self._call_with_retries(text)
        if self.settings.cache_ttl_seconds:
            self._cache[key] = _CacheEntry(
                response=response, expires_at=self._clock() + self.settings.cache_ttl_seconds
            )
        return self._result(response, started, cache_hit=False, retries=retries)

    async def _call_with_retries(self, text: str) -> tuple[ProviderResponse, int]:
        for attempt in range(self.settings.max_retries + 1):
            try:
                return await self.provider.classify(text), attempt
            except ProviderOutputError:
                raise
            except ProviderFailure as exc:
                if not self._is_retryable(exc) or attempt == self.settings.max_retries:
                    raise
                delay = min(self.settings.retry_backoff_seconds * (2**attempt), 2.0)
                await self._sleep(delay)
        raise RuntimeError("unreachable")

    @staticmethod
    def _is_retryable(error: ProviderFailure) -> bool:
        return error.kind in {"timeout", "rate_limited", "upstream"}

    def _result(
        self, response: ProviderResponse, started: float, cache_hit: bool, retries: int
    ) -> ClassificationResult:
        return ClassificationResult(
            **response.classification.model_dump(),
            metadata=OperationalMetadata(
                provider=self.provider.name,
                model=self.provider.model,
                duration_ms=round((self._clock() - started) * 1000, 2),
                cache_hit=cache_hit,
                retries=retries,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            ),
        )