from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models import Category, ProviderClassification, Urgency
from backend.prompts import PROMPT_PATH, SYSTEM_PROMPT
from backend.providers import (
    OpenAIResponsesProvider,
    ProviderFailure,
    ProviderOutputError,
    ProviderResponse,
    StubProvider,
)
from backend.service import ClassifierService
from backend.settings import Settings


class ScriptedProvider:
    name = "scripted"
    model = "test-model"

    def __init__(self, actions: list[object]) -> None:
        self.actions = actions
        self.calls = 0
        self.repair_calls = 0
        self.repair_errors: list[str] = []

    async def _next(self) -> ProviderResponse:
        self.calls += 1
        action = self.actions.pop(0)
        if isinstance(action, Exception):
            raise action
        return action

    async def classify(self, _: str) -> ProviderResponse:
        return await self._next()

    async def repair(self, _: str, validation_error: str) -> ProviderResponse:
        self.repair_calls += 1
        self.repair_errors.append(validation_error)
        return await self._next()


def good_response() -> ProviderResponse:
    return ProviderResponse(
        classification=ProviderClassification(
            category=Category.BUG,
            urgency=Urgency.NORMAL,
            confidence=0.9,
            reason="The message reports a reproducible product failure.",
        ),
        input_tokens=12,
        output_tokens=9,
    )


def client_for(provider, **overrides) -> TestClient:
    settings = Settings(
        llm_enabled=overrides.get("llm_enabled", True),
        llm_mode=overrides.get("llm_mode", "stub"),
        openai_api_key=overrides.get("openai_api_key"),
        max_retries=overrides.get("max_retries", 2),
        retry_backoff_seconds=overrides.get("retry_backoff_seconds", 0),
        cache_ttl_seconds=overrides.get("cache_ttl_seconds", 60),
        input_cost_per_million_usd=overrides.get("input_cost_per_million_usd", 0),
        output_cost_per_million_usd=overrides.get("output_cost_per_million_usd", 0),
        quarantine_path=overrides.get(
            "quarantine_path", Path("runtime/test-quarantine.jsonl")
        ),
    )
    kwargs = {}
    if "sleep" in overrides:
        kwargs["sleep"] = overrides["sleep"]
    if "jitter_fn" in overrides:
        kwargs["jitter_fn"] = overrides["jitter_fn"]
    service = ClassifierService(settings, provider, **kwargs)
    return TestClient(create_app(settings, service))


def test_happy_path_and_metadata() -> None:
    response = client_for(StubProvider()).post(
        "/llm/classify", json={"text": "The app crashes"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "bug"
    assert body["urgency"] == "normal"
    assert 0 <= body["confidence"] <= 1
    assert body["metadata"]["provider"] == "deterministic-stub"
    assert body["metadata"]["prompt_version"] == "support-classifier-v1"
    assert body["metadata"]["repair_attempted"] is False
    assert body["metadata"]["repair_count"] == 0


def test_validation_rejects_blank_and_unknown_fields() -> None:
    client = client_for(StubProvider())
    assert client.post("/llm/classify", json={"text": "  "}).status_code == 400
    assert (
        client.post("/llm/classify", json={"text": "hello", "extra": True}).status_code
        == 400
    )


def test_versioned_prompt_contains_all_five_required_parts_and_examples() -> None:
    assert PROMPT_PATH.name == "support-classifier-v1.md"
    assert "## 1. Role / job" in SYSTEM_PROMPT
    assert "## 2. Exact output structure" in SYSTEM_PROMPT
    assert "## 3. Rules" in SYSTEM_PROMPT
    assert "## 4. Uncertainty behaviour" in SYSTEM_PROMPT
    assert "## 5. Examples" in SYSTEM_PROMPT
    assert SYSTEM_PROMPT.count("### Example") == 3
    assert "untrusted data" in SYSTEM_PROMPT


def test_invalid_output_is_repaired_exactly_once_using_validation_error(
    tmp_path: Path,
) -> None:
    provider = ScriptedProvider(
        [
            ProviderOutputError("not-json", "invalid JSON at line 1"),
            good_response(),
        ]
    )
    quarantine = tmp_path / "quarantine.jsonl"
    response = client_for(provider, quarantine_path=quarantine).post(
        "/llm/classify", json={"text": "I need help"}
    )
    assert response.status_code == 200
    assert response.json()["metadata"]["repair_attempted"] is True
    assert response.json()["metadata"]["repair_count"] == 1
    assert provider.calls == 2
    assert provider.repair_calls == 1
    assert provider.repair_errors == ["invalid JSON at line 1"]
    rows = [json.loads(line) for line in quarantine.read_text().splitlines()]
    assert [row["attempt"] for row in rows] == [1]
    assert rows[0]["raw_output"] == "not-json"
    assert rows[0]["validation_error"] == "invalid JSON at line 1"
    assert "I need help" not in quarantine.read_text()


def test_second_invalid_output_returns_422_and_quarantines_both(tmp_path: Path) -> None:
    provider = ScriptedProvider(
        [
            ProviderOutputError("bad-one", "first schema error"),
            ProviderOutputError("bad-two", "second schema error"),
        ]
    )
    quarantine = tmp_path / "quarantine.jsonl"
    response = client_for(provider, quarantine_path=quarantine).post(
        "/llm/classify", json={"text": "I need help"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_provider_output"
    assert provider.calls == 2
    assert provider.repair_calls == 1
    rows = [json.loads(line) for line in quarantine.read_text().splitlines()]
    assert [row["attempt"] for row in rows] == [1, 2]
    assert [row["validation_error"] for row in rows] == [
        "first schema error",
        "second schema error",
    ]


def test_timeout_retries_then_reports_timeout() -> None:
    provider = ScriptedProvider(
        [
            ProviderFailure("timeout"),
            ProviderFailure("timeout"),
            ProviderFailure("timeout"),
        ]
    )
    response = client_for(provider).post(
        "/llm/classify", json={"text": "I need help"}
    )
    assert response.status_code == 504
    assert provider.calls == 3


def test_transient_failure_retries() -> None:
    provider = ScriptedProvider([ProviderFailure("upstream", 503), good_response()])
    response = client_for(provider).post(
        "/llm/classify", json={"text": "I need help"}
    )
    assert response.status_code == 200
    assert response.json()["metadata"]["retries"] == 1
    assert provider.calls == 2


def test_retry_after_is_honoured_and_jitter_is_applied() -> None:
    async def scenario() -> None:
        sleeps: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        provider = ScriptedProvider(
            [ProviderFailure("rate_limited", 429, 1.25), good_response()]
        )
        settings = Settings(
            retry_backoff_seconds=0.4,
            max_retries=1,
            cache_ttl_seconds=0,
        )
        service = ClassifierService(
            settings,
            provider,
            sleep=fake_sleep,
            jitter_fn=lambda low, high: high,
        )
        result = await service.classify("I need help")
        assert result.metadata.retries == 1
        assert sleeps == [1.25]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "kind,status,expected_code",
    [
        ("request_rejected", 400, "provider_rejected"),
        ("auth_rejected", 401, "provider_auth_failed"),
        ("auth_rejected", 403, "provider_auth_failed"),
        ("unexpected", 404, "provider_failure"),
    ],
)
def test_non_retryable_client_failures_do_not_retry(
    kind: str,
    status: int,
    expected_code: str,
) -> None:
    provider = ScriptedProvider([ProviderFailure(kind, status), good_response()])
    response = client_for(provider).post(
        "/llm/classify", json={"text": "I need help"}
    )
    assert response.status_code == 502
    assert response.json()["code"] == expected_code
    assert provider.calls == 1


def test_kill_switch() -> None:
    response = client_for(StubProvider(), llm_enabled=False).post(
        "/llm/classify", json={"text": "I need help"}
    )
    assert response.status_code == 503
    assert response.json()["code"] == "llm_disabled"


def test_kill_switch_allows_startup_without_provider_credentials() -> None:
    settings = Settings(
        llm_enabled=False,
        llm_mode="openai",
        openai_api_key=None,
    )
    client = TestClient(create_app(settings=settings))
    assert client.get("/healthz").status_code == 200
    response = client.post("/llm/classify", json={"text": "I need help"})
    assert response.status_code == 503
    assert response.json()["code"] == "llm_disabled"


def test_enabled_openai_without_credentials_starts_and_returns_controlled_503() -> None:
    settings = Settings(
        llm_enabled=True,
        llm_mode="openai",
        openai_api_key=None,
    )
    client = TestClient(create_app(settings=settings))
    assert client.get("/healthz").status_code == 200
    response = client.post("/llm/classify", json={"text": "I need help"})
    assert response.status_code == 503
    assert response.json()["code"] == "provider_misconfigured"


def test_stub_mode() -> None:
    response = client_for(StubProvider()).post(
        "/llm/classify", json={"text": "Please add calendar integration"}
    )
    assert response.status_code == 200
    assert response.json()["category"] == "feature"


def test_identical_input_is_cached() -> None:
    provider = ScriptedProvider([good_response()])
    client = client_for(provider)
    first = client.post("/llm/classify", json={"text": "I need help"})
    second = client.post("/llm/classify", json={"text": "I need help"})
    assert first.json()["metadata"]["cache_hit"] is False
    assert second.json()["metadata"]["cache_hit"] is True
    assert provider.calls == 1


def test_usage_cost_metadata_and_safe_logging(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="backend.service")
    response = client_for(
        ScriptedProvider([good_response()]),
        input_cost_per_million_usd=2.0,
        output_cost_per_million_usd=8.0,
    ).post("/llm/classify", json={"text": "secret customer sentence"})
    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["input_tokens"] == 12
    assert metadata["output_tokens"] == 9
    assert metadata["estimated_cost_usd"] == 0.000096
    assert "secret customer sentence" not in caplog.text
    assert "prompt_version=support-classifier-v1" in caplog.text
    assert "repair_count=0" in caplog.text


def test_secret_hygiene_no_key_in_responses() -> None:
    response = client_for(
        ScriptedProvider([ProviderFailure("auth_rejected", 401)])
    ).post("/llm/classify", json={"text": "Bearer pretend-secret-value"})
    assert "pretend-secret-value" not in response.text


def test_openai_adapter_rejects_malformed_structured_output_and_uses_low_temperature() -> None:
    async def scenario() -> None:
        seen_payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_payloads.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": '{"category":"not-allowed"}',
                                }
                            ]
                        }
                    ]
                },
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = OpenAIResponsesProvider(
                Settings(llm_mode="openai", openai_api_key="test-only-key"),
                client=client,
            )
            with pytest.raises(ProviderOutputError) as raised:
                await provider.classify("A test support message")
            assert raised.value.raw_output == '{"category":"not-allowed"}'
            assert raised.value.validation_error
        payload = seen_payloads[0]
        assert payload["temperature"] == 0
        assert payload["input"][0]["role"] == "system"
        assert payload["input"][1] == {
            "role": "user",
            "content": [{"type": "input_text", "text": "A test support message"}],
        }

    asyncio.run(scenario())


def test_openai_adapter_carries_retry_after_on_429() -> None:
    async def scenario() -> None:
        transport = httpx.MockTransport(
            lambda _: httpx.Response(429, headers={"Retry-After": "2.5"})
        )
        async with httpx.AsyncClient(transport=transport) as client:
            provider = OpenAIResponsesProvider(
                Settings(llm_mode="openai", openai_api_key="test-only-key"),
                client=client,
            )
            with pytest.raises(ProviderFailure) as raised:
                await provider.classify("A test support message")
            assert raised.value.kind == "rate_limited"
            assert raised.value.retry_after_seconds == 2.5

    asyncio.run(scenario())


def test_managed_openai_environment_selects_replit_proxy(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_API_KEY", "managed-test-key")
    monkeypatch.setenv(
        "AI_INTEGRATIONS_OPENAI_BASE_URL", "https://proxy.example/v1/"
    )

    settings = Settings.from_env()

    assert settings.openai_api_key == "managed-test-key"
    assert settings.openai_base_url == "https://proxy.example/v1"
    assert settings.openai_provider_name == "replit-ai-integrations-openai"


def test_timeout_environment_is_capped_at_sixty_seconds(monkeypatch) -> None:
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "600")
    assert Settings.from_env().timeout_seconds == 60.0


def test_source_does_not_hardcode_or_echo_api_key() -> None:
    provider_source = (Path(__file__).resolve().parents[1] / "providers.py").read_text()
    example_env = Path(__file__).resolve().parents[2] / ".env.example"
    assert "sk-" not in provider_source
    assert "print(" not in provider_source
    assert not any(
        line.strip().startswith("OPENAI_API_KEY=")
        for line in example_env.read_text().splitlines()
    )
