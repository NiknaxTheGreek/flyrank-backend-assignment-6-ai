"""Provider adapters with a small, testable interface."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from .models import Category, ProviderClassification, Urgency
from .prompts import REPAIR_PROMPT, SYSTEM_PROMPT
from .settings import Settings


class ProviderFailure(Exception):
    """A sanitized provider failure suitable for public error mapping."""

    def __init__(self, kind: str, status_code: int | None = None) -> None:
        self.kind = kind
        self.status_code = status_code
        super().__init__(kind)


class ProviderOutputError(Exception):
    """Raised when an upstream response cannot satisfy our schema."""

    def __init__(self, raw_output: str | None = None) -> None:
        self.raw_output = raw_output
        super().__init__("provider output was not valid structured JSON")


@dataclass(frozen=True)
class ProviderResponse:
    classification: ProviderClassification
    input_tokens: int | None = None
    output_tokens: int | None = None


class Provider(Protocol):
    name: str
    model: str

    async def classify(self, text: str) -> ProviderResponse: ...

    async def repair(self, text: str) -> ProviderResponse: ...


class StubProvider:
    """Deterministic local classifier used for tests and credential-free demos."""

    name = "deterministic-stub"
    model = "rules-v1"

    async def classify(self, text: str) -> ProviderResponse:
        message = text.lower()
        if any(token in message for token in ("charged", "charge", "invoice", "refund", "payment", "card")):
            category = Category.BILLING
            reason = "The message describes a payment, charge, invoice, or refund concern."
        elif any(token in message for token in ("crash", "error", "broken", "not work", "bug", "fails")):
            category = Category.BUG
            reason = "The message reports broken or failing product behavior."
        elif any(token in message for token in ("feature", "add", "would love", "please support", "integration")):
            category = Category.FEATURE
            reason = "The message asks for new or expanded product capability."
        else:
            category = Category.OTHER
            reason = "The message does not clearly match billing, bug, or feature support."

        urgency = (
            Urgency.HIGH
            if any(token in message for token in ("urgent", "asap", "immediately", "locked out", "cannot access"))
            else Urgency.LOW
            if any(token in message for token in ("when you can", "no rush", "curious"))
            else Urgency.NORMAL
        )
        return ProviderResponse(
            classification=ProviderClassification(
                category=category,
                urgency=urgency,
                confidence=0.84,
                reason=reason,
            )
        )

    async def repair(self, text: str) -> ProviderResponse:
        return await self.classify(text)


class OpenAIResponsesProvider:
    """OpenAI Responses API adapter using JSON Schema structured output."""

    name = "openai"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        if not settings.openai_api_key:
            raise ProviderFailure("misconfigured")
        self.name = settings.openai_provider_name
        self.model = settings.openai_model
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url
        self._timeout = settings.timeout_seconds
        self._client = client

    async def classify(self, text: str) -> ProviderResponse:
        return await self._request(text, repair=False)

    async def repair(self, text: str) -> ProviderResponse:
        return await self._request(text, repair=True)

    async def _request(self, text: str, *, repair: bool) -> ProviderResponse:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        system_text = SYSTEM_PROMPT if not repair else f"{SYSTEM_PROMPT}\n\n{REPAIR_PROMPT}"
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_text}],
                },
                {"role": "user", "content": [{"type": "input_text", "text": text}]},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "support_classification",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["category", "urgency", "confidence", "reason"],
                        "properties": {
                            "category": {"type": "string", "enum": [item.value for item in Category]},
                            "urgency": {"type": "string", "enum": [item.value for item in Urgency]},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "reason": {"type": "string", "minLength": 1, "maxLength": 240},
                        },
                    },
                }
            },
        }
        try:
            response = await client.post(
                f"{self._base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise ProviderFailure("timeout") from exc
        except httpx.HTTPError as exc:
            raise ProviderFailure("upstream") from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code == 429:
            raise ProviderFailure("rate_limited", 429)
        if response.status_code >= 500:
            raise ProviderFailure("upstream", response.status_code)
        if response.status_code in {400, 401, 403}:
            raise ProviderFailure("request_rejected", response.status_code)
        if response.status_code >= 400:
            raise ProviderFailure("unexpected", response.status_code)

        raw_text: str | None = None
        try:
            body = response.json()
            raw_text = _extract_output_text(body)
            classification = ProviderClassification.model_validate_json(raw_text)
            usage = body.get("usage") or {}
            return ProviderResponse(
                classification=classification,
                input_tokens=_optional_int(usage.get("input_tokens")),
                output_tokens=_optional_int(usage.get("output_tokens")),
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderOutputError(raw_text) from exc


def _extract_output_text(body: dict[str, Any]) -> str:
    for item in body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise ValueError("no output text present")


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def build_provider(settings: Settings) -> Provider:
    if settings.llm_mode == "stub":
        return StubProvider()
    if settings.llm_mode == "openai":
        return OpenAIResponsesProvider(settings)
    raise ProviderFailure("misconfigured")
