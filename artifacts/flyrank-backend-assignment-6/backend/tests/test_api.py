from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models import Category, ProviderClassification, Urgency
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

    async def classify(self, _: str) -> ProviderResponse:
        self.calls += 1
        action = self.actions.pop(0)
        if isinstance(action, Exception):
            raise action
        return action


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
        llm_mode="stub",
        max_retries=overrides.get("max_retries", 2),
        retry_backoff_seconds=0,
        cache_ttl_seconds=60,
    )
    service = ClassifierService(settings, provider)
    return TestClient(create_app(settings, service))


def test_happy_path_and_metadata() -> None:
    response = client_for(StubProvider()).post("/llm/classify", json={"text": "The app crashes"})
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "bug"
    assert body["urgency"] == "normal"
    assert 0 <= body["confidence"] <= 1
    assert body["metadata"]["provider"] == "deterministic-stub"


def test_validation_rejects_blank_and_unknown_fields() -> None:
    client = client_for(StubProvider())
    assert client.post("/llm/classify", json={"text": "  "}).status_code == 400
    assert client.post("/llm/classify", json={"text": "hello", "extra": True}).status_code == 400


def test_structured_output_rejection() -> None:
    response = client_for(ScriptedProvider([ProviderOutputError()])).post(
        "/llm/classify", json={"text": "I need help"}
    )
    assert response.status_code == 502
    assert response.json()["code"] == "invalid_provider_output"


def test_timeout_retries_then_reports_timeout() -> None:
    provider = ScriptedProvider([ProviderFailure("timeout"), ProviderFailure("timeout"), ProviderFailure("timeout")])
    response = client_for(provider).post("/llm/classify", json={"text": "I need help"})
    assert response.status_code == 504
    assert provider.calls == 3


def test_transient_failure_retries() -> None:
    provider = ScriptedProvider([ProviderFailure("upstream", 503), good_response()])
    response = client_for(provider).post("/llm/classify", json={"text": "I need help"})
    assert response.status_code == 200
    assert response.json()["metadata"]["retries"] == 1
    assert provider.calls == 2


@pytest.mark.parametrize("status", [400, 401, 403])
def test_non_retryable_client_failures_do_not_retry(status: int) -> None:
    provider = ScriptedProvider([ProviderFailure("request_rejected", status), good_response()])
    response = client_for(provider).post("/llm/classify", json={"text": "I need help"})
    assert response.status_code == 502
    assert provider.calls == 1


def test_kill_switch() -> None:
    response = client_for(StubProvider(), llm_enabled=False).post("/llm/classify", json={"text": "I need help"})
    assert response.status_code == 503
    assert response.json()["code"] == "llm_disabled"


def test_stub_mode() -> None:
    response = client_for(StubProvider()).post("/llm/classify", json={"text": "Please add calendar integration"})
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


def test_secret_hygiene_no_key_in_responses() -> None:
    response = client_for(ScriptedProvider([ProviderFailure("request_rejected", 401)])).post(
        "/llm/classify", json={"text": "Bearer pretend-secret-value"}
    )
    assert "pretend-secret-value" not in response.text


def test_openai_adapter_rejects_malformed_structured_output() -> None:
    async def scenario() -> None:
        transport = httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "output": [{"content": [{"type": "output_text", "text": '{"category":"not-allowed"}'}]}]
                },
            )
        )
        async with httpx.AsyncClient(transport=transport) as client:
            provider = OpenAIResponsesProvider(
                Settings(llm_mode="openai", openai_api_key="test-only-key"),
                client=client,
            )
            with pytest.raises(ProviderOutputError):
                await provider.classify("A test support message")

    asyncio.run(scenario())


def test_managed_openai_environment_selects_replit_proxy(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_API_KEY", "managed-test-key")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://proxy.example/v1/")

    settings = Settings.from_env()

    assert settings.openai_api_key == "managed-test-key"
    assert settings.openai_base_url == "https://proxy.example/v1"
    assert settings.openai_provider_name == "replit-ai-integrations-openai"


def test_source_does_not_hardcode_or_echo_api_key() -> None:
    provider_source = (
        Path(__file__).resolve().parents[1] / "providers.py"
    ).read_text()
    example_env = Path(__file__).resolve().parents[2] / ".env.example"
    assert "sk-" not in provider_source
    assert "print(" not in provider_source
    assert not any(
        line.strip().startswith("OPENAI_API_KEY=")
        for line in example_env.read_text().splitlines()
    )