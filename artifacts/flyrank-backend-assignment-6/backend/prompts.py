"""Versioned prompt contract for Assignment 6."""

from __future__ import annotations

from pathlib import Path

PROMPT_VERSION = "support-classifier-v1"
PROMPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "prompts"
    / f"{PROMPT_VERSION}.md"
)
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_repair_prompt(validation_error: str) -> str:
    """Create the single schema-repair instruction from the observed error."""

    safe_error = validation_error.strip()[:1500] or "schema validation failed"
    return (
        "The previous model answer failed the required JSON schema. "
        "This is the only repair attempt. Correct the answer and return one JSON object only. "
        "Do not add prose, markdown, or extra keys.\n\n"
        f"Validation error:\n{safe_error}"
    )
