# FlyRank Backend Assignment 6 — Connect to an AI API

This submission exposes a small FastAPI classification endpoint that treats model output as untrusted data. The primary contract is `POST /llm/classify`; the Replit-routed alias is `POST /api/llm/classify`.

Start with [`JOB-CARD.md`](JOB-CARD.md): it defines the model job, trusted schema, uncertainty, prompt version, retry/repair policy, kill switch, observability, and failure behaviour.

## Request and trusted response

Request:

```json
{"text":"I was charged twice and need a refund."}
```

A successful response contains:

- `category`: `billing`, `bug`, `feature`, or `other`
- `urgency`: `low`, `normal`, or `high`
- `confidence`: numeric `0..1`
- `reason`: concise, non-blank explanation
- `metadata`: provider, model, prompt version, latency, cache status, transport retries, whether repair was used, token counts, and estimated cost when explicit pricing is configured

The Pydantic schema is the trust boundary. Provider text never bypasses it.

## Versioned prompt and one repair attempt

The current prompt is `support-classifier-v1` in `backend/prompts.py`.

If the first provider answer is invalid JSON or fails the schema, the service:

1. quarantines the invalid output with an input hash, timestamp, prompt version, and attempt number;
2. performs **exactly one** repair call;
3. validates the repair response through the same schema;
4. returns HTTP **422** if the repaired response is still invalid.

There is no silent coercion and no second repair loop.

## Provider failures and retries

Transport retry is separate from schema repair. Only timeout, rate-limit, and upstream failures are retried, using bounded exponential backoff. Client/request-rejection failures are not retried.

| Situation | Status | Error code |
| --- | ---: | --- |
| Invalid body / blank text | 400 | `invalid_input` |
| Invalid output after one repair | 422 | `invalid_provider_output` |
| Kill switch disabled | 503 | `llm_disabled` |
| Provider timeout after retries | 504 | `provider_timeout` |
| Provider rate limit after retries | 429 | `provider_rate_limited` |
| Provider outage after retries | 503 | `provider_unavailable` |
| Provider request/auth rejection | 502 | `provider_rejected` |
| Unexpected internal failure | 500 | `unexpected_failure` |

## Kill switch

`LLM_ENABLED=false` disables classification without preventing application startup. This remains true even when `LLM_MODE=openai` is selected and no live provider credential exists. `/healthz` still returns healthy and classification returns a controlled `503 llm_disabled` response without contacting a provider.

## Provider modes

`LLM_MODE=stub` is deterministic and is used for tests and credential-free demos.

`LLM_MODE=openai` uses an OpenAI-compatible Responses API with strict JSON Schema output. Credentials are supplied only through environment/managed-secret injection. Replit AI Integrations are supported through the managed base URL/key variables. No credential is committed.

## Observability and cost

The service logs operational metadata only: provider, model, prompt version, duration, cache hit, retries, repair flag, token counts, and estimated cost. It intentionally does **not** log the customer message, API key, Authorization header, or raw provider response.

Cost is only calculated when explicit per-million-token rates are configured. Zero-valued defaults mean no price has been asserted.

## Run

From the repository root:

```bash
PYTHONPATH=artifacts/flyrank-backend-assignment-6 \
python -m uvicorn backend.main:app --app-dir artifacts/flyrank-backend-assignment-6 --host 0.0.0.0 --port 8000
```

Then:

```bash
curl -X POST http://localhost:8000/llm/classify \
  -H 'content-type: application/json' \
  -d '{"text":"The mobile app crashes after login."}'
```

## Verify

```bash
PYTHONPATH=artifacts/flyrank-backend-assignment-6 \
python -m pytest artifacts/flyrank-backend-assignment-6/backend/tests -q

cd artifacts/flyrank-backend-assignment-6
PYTHONPATH=. python -m backend.eval_runner
```

GitHub Actions runs the same backend contract checks plus a real local HTTP checkpoint using the deterministic provider.

## Existing live-provider evidence

`docs/verification.md` records the previously executed genuine managed-provider request separately from deterministic tests. That evidence includes the real provider/model, HTTP result, validated classification, latency, and token usage without exposing credentials. It is not rewritten as a new live provider call by CI.

## Repository layout note

The original Replit workspace contains frontend/tooling files around the assignment. The actual Assignment 6 submission is isolated under `artifacts/flyrank-backend-assignment-6/`; the root README points directly here so reviewers do not need to infer the submission path.

## AI Rematch

This is the independent AI-generated implementation. The later human-vs-AI comparison remains a separate project stage and is not claimed complete here.
