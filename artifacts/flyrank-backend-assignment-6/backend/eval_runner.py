"""Run the labeled evaluation set and report observed, not invented, scores."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from .providers import StubProvider


async def run() -> dict[str, object]:
    cases_path = Path(__file__).with_name("eval_cases.json")
    cases = json.loads(cases_path.read_text())
    provider = StubProvider()
    observed = []
    correct_category = 0
    correct_urgency = 0
    correct_both = 0
    for case in cases:
        result = await provider.classify(case["text"])
        category_ok = result.classification.category.value == case["category"]
        urgency_ok = result.classification.urgency.value == case["urgency"]
        correct_category += category_ok
        correct_urgency += urgency_ok
        correct_both += category_ok and urgency_ok
        observed.append(
            {
                "id": case["id"],
                "expected": {"category": case["category"], "urgency": case["urgency"]},
                "observed": {
                    "category": result.classification.category.value,
                    "urgency": result.classification.urgency.value,
                },
                "category_correct": category_ok,
                "urgency_correct": urgency_ok,
            }
        )
    count = len(cases)
    report = {
        "mode": "stub",
        "case_count": count,
        "category_accuracy": correct_category / count,
        "urgency_accuracy": correct_urgency / count,
        "joint_accuracy": correct_both / count,
        "cases": observed,
    }
    Path(__file__).with_name("eval_results.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run()), indent=2))