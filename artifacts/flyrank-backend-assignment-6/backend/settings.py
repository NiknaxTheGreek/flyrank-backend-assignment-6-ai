"""Environment-only runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    llm_enabled: bool = True
    llm_mode: str = "stub"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_provider_name: str = "openai"
    openai_model: str = "gpt-4.1-mini"
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.15
    cache_ttl_seconds: float = 300.0

    @classmethod
    def from_env(cls) -> "Settings":
        managed_base_url = os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "").strip()
        direct_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        return cls(
            llm_enabled=_as_bool(os.getenv("LLM_ENABLED"), True),
            llm_mode=os.getenv("LLM_MODE", "stub").strip().lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY")
            or os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY"),
            openai_base_url=(managed_base_url or direct_base_url).rstrip("/"),
            openai_provider_name=(
                "replit-ai-integrations-openai" if managed_base_url else "openai"
            ),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            max_retries=max(0, min(int(os.getenv("LLM_MAX_RETRIES", "2")), 4)),
            retry_backoff_seconds=max(
                0.0, min(float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "0.15")), 2.0)
            ),
            cache_ttl_seconds=max(0.0, float(os.getenv("LLM_CACHE_TTL_SECONDS", "300"))),
        )