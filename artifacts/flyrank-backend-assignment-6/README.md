# FlyRank Backend Assignment 6 — Connect to an AI API

This submission exposes one narrow FastAPI LLM job: `POST /llm/classify` converts an unstructured customer-support message into a strict validated classification. The Replit-routed alias is `POST /api/llm/classify`.

Start with [`JOB-CARD.md`](JOB-CARD.md). It defines the job, input, closed output schema, uncertainty behaviour, failure behaviour, and operational boundaries before the model is called.

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
- `metadata`: provider, model, prompt version, latency, cache status, transport retries, repair count, token counts, and estimated cost when explicit pricing is configured

The Pydantic schema is the trust boundary. Provider text never bypasses it.

## Install and run

Python 3.11+ is sufficient. From the repository root:

```bash
python -m pip install "fastapi>=0.115" "httpx>=0.28" "pydantic>=2.10" "uvicorn>=0.30"

PYTHONPATH=artifacts/flyrank-backend-assignment-6 \
LLM_MODE=stub LLM_ENABLED=true \
python -m uvicorn backend.main:app \
  --app-dir artifacts/flyrank-backend-assignment-6 \
  --host 0.0.0.0 --port 8000
```

Valid request:

```bash
curl -i -X POST http://localhost:8000/llm/classify \
  -H 'content-type: application/json' \
  -d '{"text":"The mobile app crashes after login."}'
```

The deterministic stub returns HTTP `200` with a schema-valid `bug` classification and metadata.

Invalid input is rejected before any provider call:

```bash
curl -i -X POST http://localhost:8000/llm/classify \
  -H 'content-type: application/json' \
  -d '{"text":"   "}'
```

Expected controlled response:

```json
{"error":"invalid request body","code":"invalid_input"}
```

with HTTP `400`.

## Versioned prompt

The operational prompt is stored separately from route code at:

[`prompts/support-classifier-v1.md`](prompts/support-classifier-v1.md)

Prompt version: `support-classifier-v1`.

It contains the five required parts:

1. role/job;
2. exact output structure;
3. rules;
4. uncertainty behaviour;
5. three examples covering a normal case, ambiguous case, and hostile prompt-injection case.

Customer text is sent as a separate `user` input. The provider request uses temperature `0` and strict JSON Schema output.

## Parse, validate, repair, quarantine

If the first provider answer is invalid JSON or fails the trusted schema, the service:

1. records the invalid output, prompt version, input hash, and actual validation error in an ignored runtime quarantine JSONL file;
2. sends the validation error into **exactly one** repair call;
3. validates the repaired answer through the same Pydantic schema;
4. returns HTTP **422** if the repaired answer is still invalid.

There is no silent coercion and no second repair loop. The original customer text is not written to the quarantine file.

## Provider failures and retries

Transport retry is deliberately separate from schema repair.

Retryable:

- timeout;
- HTTP `429`;
- upstream `5xx`.

Not retryable:

- HTTP `400`;
- provider authentication `401/403`;
- other ordinary client rejection.

The service uses bounded exponential backoff plus jitter and honours a numeric `Retry-After` header when supplied. The configured timeout is clamped to at most 60 seconds; the default is 30 seconds. This implementation uses `httpx` directly rather than an SDK with hidden/default retry behaviour, so the retry count is controlled only by this service.

| Situation | Status | Error code |
| --- | ---: | --- |
| Invalid body / blank text | 400 | `invalid_input` |
| Invalid output after one repair | 422 | `invalid_provider_output` |
| Kill switch disabled | 503 | `llm_disabled` |
| Provider timeout after retries | 504 | `provider_timeout` |
| Provider rate limit after retries | 429 | `provider_rate_limited` |
| Provider outage after retries | 503 | `provider_unavailable` |
| Provider authentication failure | 502 | `provider_auth_failed` |
| Provider request rejection | 502 | `provider_rejected` |
| Missing live-provider configuration | 503 | `provider_misconfigured` |

## Kill switch and provider switching

`LLM_ENABLED=false` disables classification without preventing application startup. `/healthz` remains available and classification returns `503 llm_disabled` without contacting a provider.

`LLM_MODE=stub` selects the deterministic local provider.

`LLM_MODE=openai` selects the OpenAI-compatible Responses API provider. Configuration is environment-only:

```text
OPENAI_API_KEY=<secret, never committed>
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

Replit AI Integrations are also supported through `AI_INTEGRATIONS_OPENAI_BASE_URL` and `AI_INTEGRATIONS_OPENAI_API_KEY`. `.env.example` contains placeholders/configuration only, never credentials.

## Observability and cost

Successful calls log operational fields only: prompt version, provider, model, duration, transport retry count, repair count, input tokens, output tokens, cache state, and configured-rate cost estimate. Logs intentionally omit the customer message, API key, Authorization header, and raw provider response.

Example metadata calculation covered by the tests:

```text
input_tokens=12
output_tokens=9
input_rate=$2.00 / 1M
output_rate=$8.00 / 1M
estimated_cost_usd=$0.000096
```

Rates are explicit configuration; zero means "cost rate not configured" rather than inventing a price.

### 10,000-request/day estimate

The genuine managed-provider checkpoint recorded `130` input tokens and `31` output tokens for one `gpt-4.1-mini` request. On 2026-08-24, OpenAI's official model page listed standard direct-API text pricing of **$0.40 / 1M input tokens** and **$1.60 / 1M output tokens**:

`https://developers.openai.com/api/docs/models/gpt-4.1-mini`

Using that observed token shape and direct OpenAI list pricing:

```text
one request = (130 × $0.40 + 31 × $1.60) / 1,000,000
            = $0.0001016

10,000 requests/day ≈ $1.016/day
```

This is a direct-OpenAI list-price estimate, not a claim about Replit AI Integrations billing, discounts, caching, or future pricing.

## Labelled evaluation

The current deterministic evaluation contains 12 labelled cases, including ambiguous cases. It therefore exceeds the required eight-case minimum.

- Evaluation date: **2026-08-24**
- Prompt version: `support-classifier-v1`
- Evaluation provider/model: `deterministic-stub` / `rules-v1`
- Category accuracy: **11/12 = 0.9167**
- Urgency accuracy: **12/12 = 1.0000**
- Joint accuracy: **11/12 = 0.9167**
- Known miss retained honestly: `bug-access`, expected `bug/high`, observed `other/high`

The deterministic evaluation is not represented as a real LLM call.

## Genuine external-provider evidence

A genuine managed OpenAI-compatible call was executed on **2026-08-22** through Replit AI Integrations using `gpt-4.1-mini`. The observed request to `POST /llm/classify` returned HTTP `200`, `billing/high`, confidence `0.95`, 130 input tokens, 31 output tokens, and approximately 1.95 seconds end-to-end latency. No credential was recorded.

That executed evidence is preserved in [`docs/verification.md`](docs/verification.md). GitHub Actions does not pretend to make a fresh paid-provider request because no provider credential is exposed to CI.

## Verify

```bash
PYTHONPATH=artifacts/flyrank-backend-assignment-6 \
python -m pytest artifacts/flyrank-backend-assignment-6/backend/tests -q

cd artifacts/flyrank-backend-assignment-6
PYTHONPATH=. python -m backend.eval_runner
```

GitHub Actions runs compilation, the backend contract suite, the labelled evaluation, and a real local HTTP checkpoint using the deterministic provider.

## Identified improvement

The known `bug-access` evaluation miss shows that the deterministic stub's keyword rules do not recognize every access-related product failure. A future prompt/model comparison should test whether live-model classification improves that case without reducing precision on billing and feature requests. The measured miss is intentionally retained rather than changing labels to inflate the score.

## Repository layout

The original Replit workspace contains surrounding frontend/tooling files. The actual Assignment 6 submission is isolated under `artifacts/flyrank-backend-assignment-6/`; the root README points directly here so reviewers do not need to infer the submission path.

## AI Rematch

This repository is the independent AI-generated implementation. The later human-vs-AI comparison remains a separate project stage and is not claimed complete here.
