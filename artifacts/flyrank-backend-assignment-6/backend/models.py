"""Trusted API shapes. Provider responses never bypass these models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(str, Enum):
    BILLING = "billing"
    BUG = "bug"
    FEATURE = "feature"
    OTHER = "other"


class Urgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class SupportMessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text must not be blank")
        return normalized


class ProviderClassification(BaseModel):
    """Only this schema is accepted from an LLM or test double."""

    model_config = ConfigDict(extra="forbid")

    category: Category
    urgency: Urgency
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=240)

    @field_validator("reason")
    @classmethod
    def concise_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must not be blank")
        return normalized


class OperationalMetadata(BaseModel):
    provider: str
    model: str
    prompt_version: str
    duration_ms: float = Field(ge=0)
    cache_hit: bool
    retries: int = Field(ge=0)
    repair_attempted: bool = False
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)


class ClassificationResult(ProviderClassification):
    metadata: OperationalMetadata


class ErrorResponse(BaseModel):
    error: str
    code: str
