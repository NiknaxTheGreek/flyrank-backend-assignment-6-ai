"""Append-only quarantine for invalid model outputs.

The file is runtime evidence and is ignored by Git. It never stores API keys or
Authorization headers.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class QuarantineSink:
    def __init__(self, path: Path) -> None:
        self.path = path

    def record(self, *, text: str, raw_output: str | None, attempt: int, prompt_version: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry: dict[str, Any] = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "attempt": attempt,
            "prompt_version": prompt_version,
            "raw_output": raw_output,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
