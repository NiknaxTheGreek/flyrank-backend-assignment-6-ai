# FlyRank Backend Assignment 6 — LLM behind an API

A compact FastAPI service for structured customer-support classification, paired with a browser console. The assignment contract is `POST /llm/classify`; the Replit-routed browser endpoint is also available at `POST /api/llm/classify`.

## Contract

Request:

```json
{"text":"I was charged twice and need a refund."}
```

Successful response fields are validated after every provider call:

- `category`: `billing`, `bug`, `feature`, or `other`
- `urgency`: `low`, `normal`, or `high`
- `confidence`: numeric, inclusive `0..1`
- `reason`: concise, input-grounded string
- `metadata`: provider/model, duration, cache hit, retries, and provider token usage when supplied

Model output is untrusted. Invalid JSON, unexpected fields, invalid enums, out-of-range confidence, or missing fields return a safe `502 invalid_provider_output`.

## Run locally

```bash
uv run python -m uvicorn backend.main:app --app-dir artifacts/flyrank-backend-assignment-6 --host 0.0.0.0 --port 8000
curl -X POST http://localhost:8000/llm/classify \
  -H 'content-type: application/json' \
  -d '{"text":"The mobile app crashes after login."}'
```

The default is deterministic `stub` mode. Copy `.env.example` and use environment variables; never commit or hard-code credentials.

## OpenAI Responses adapter

Set `LLM_MODE=openai` and optionally set `OPENAI_MODEL`. The adapter calls the OpenAI-compatible Responses API with strict JSON Schema output. It supports either a direct `OPENAI_API_KEY` or Replit AI Integrations: when Replit provides `AI_INTEGRATIONS_OPENAI_BASE_URL` and `AI_INTEGRATIONS_OPENAI_API_KEY`, it selects that managed proxy automatically. Those managed values are provisioned by Replit and must never be copied into source or `.env` files. The adapter uses a finite 30-second default timeout and retries only timeout, HTTP 429, and 5xx-style upstream failures with bounded exponential backoff. It does not retry 400, 401, or 403.

## Failure behavior

| Situation | Status | Error code |
| --- | ---: | --- |
| Invalid body / blank text | 400 | `invalid_input` |
| Kill switch disabled | 503 | `llm_disabled` |
| Provider timeout | 504 | `provider_timeout` |
| Provider rate limit | 429 | `provider_rate_limited` |
| Provider 5xx/outage | 503 | `provider_unavailable` |
| Invalid provider JSON/schema | 502 | `invalid_provider_output` |
| Auth/client rejection | 502 | `provider_rejected` |
| Unexpected internal failure | 500 | `unexpected_failure` |

The response intentionally never includes provider headers, raw body, API keys, or stack traces.

## Verify

```bash
PYTHONPATH=artifacts/flyrank-backend-assignment-6 uv run pytest artifacts/flyrank-backend-assignment-6/backend/tests -q
PYTHONPATH=artifacts/flyrank-backend-assignment-6 uv run python -m backend.eval_runner
pnpm --filter @workspace/flyrank-backend-assignment-6 run typecheck
```

Read `docs/verification.md`, `docs/requirements-audit.md`, and `docs/source-gap-notes.md` for recorded evidence and boundaries.

The verification evidence includes one genuine Replit AI Integrations checkpoint through `POST /llm/classify`, kept separate from the deterministic-stub evaluation and mocked adapter tests.

## Evaluation

`backend/eval_cases.json` contains 12 labeled examples covering all four categories and urgency levels. `backend/eval_runner.py` evaluates the selected adapter and writes observed results to `backend/eval_results.json`; it calculates accuracy from comparison results, not declared scores.

## S4 rematch

The human-vs-AI S4 rematch comparison is explicitly **pending** until the separate human Assignment 6 exists. This project does not inspect or use that implementation.