# Verification evidence

This file separates the current repaired-code verification from the earlier genuine managed-provider checkpoint. No fresh live-provider call is claimed for GitHub Actions because no provider credential is exposed to that workflow.

## Current repaired-code gate — 2026-08-24

GitHub Actions run `32702780162` executed the current Assignment 6 branch on an Ubuntu hosted runner with Python 3.13.

| Check | Observed result |
| --- | --- |
| Python compilation | **PASS** |
| Backend contract suite | **19 passed**; one non-failing TestClient deprecation warning |
| Labelled deterministic evaluation | 12 cases; category **11/12 (0.9167)**, urgency **12/12 (1.0000)**, joint **11/12 (0.9167)** |
| Known eval miss | `bug-access`: expected `bug/high`, observed `other/high`; retained as the true measured result |
| Uvicorn health probe | **PASS** |
| Real HTTP request to local stub endpoint | **PASS** — returned validated `bug/normal` result |
| Prompt provenance | `support-classifier-v1` present in response metadata |
| Repair metadata | normal request recorded `repair_attempted=false` |
| HTTP checkpoint marker | `STUB_HTTP_GATE=PASS` |

The deterministic test suite additionally verifies the repaired failure contract rather than merely inspecting source: first invalid structured provider output is quarantined and repaired exactly once; a second invalid output returns HTTP 422; timeout/upstream failures retry while client failures do not; the kill switch permits startup with live-provider mode selected but no credential; cache behaviour works; cost is calculated from explicit configured rates; and operational logs omit the test customer message.

These tests use injected providers and temporary quarantine files where appropriate, so they do not require or expose an external API credential.

## Initial build evidence — 2026-08-22

| Check | Observed result |
| --- | --- |
| Original backend suite | **14 passed** |
| Original labelled evaluation | 12 cases; category **11/12**, urgency **12/12**, joint **11/12** |
| Python dependency audit | All 27 installed packages compatible |
| API code generation/type checks | Completed |
| Frontend/workspace type check | Completed |
| Vite production build | Completed |
| Routed FastAPI probe | `GET /api/llm/healthz` returned `{"status":"ok"}`; `POST /api/llm/classify` returned a validated `bug` result |
| Browser preview | Console loaded with the FastAPI health indicator online; screenshot saved as `screenshots/flyrank-console.jpg` |

## Genuine managed-provider checkpoint — 2026-08-22

**Status: passed — genuine managed-provider request.**

This checkpoint predates the current repair and remains valid evidence that the provider adapter was exercised against an actual managed OpenAI-compatible service. It is distinct from the deterministic stub evaluation and mocked adapter tests. Replit AI Integrations provisioned the managed proxy without placing a credential in source. A temporary FastAPI process ran with `LLM_MODE=openai` and received a real `POST /llm/classify` request.

| Field | Observed value |
| --- | --- |
| Provider | `replit-ai-integrations-openai` |
| Model | `gpt-4.1-mini` |
| Endpoint | `POST /llm/classify` |
| HTTP outcome | `200 OK` |
| Input | “My subscription was charged twice and I need an urgent refund.” |
| Validated classification | `billing`, `high`, confidence `0.95` |
| Validated reason | “Customer reports being charged twice and requests an urgent refund.” |
| End-to-end HTTP latency | `1951.41 ms` |
| API metadata duration | `1941.13 ms` |
| Cache hit | `false` |
| Retries | `0` |
| Input tokens | `130` |
| Output tokens | `31` |

No provider credential, request Authorization header, raw provider response, or other secret material is recorded here.
