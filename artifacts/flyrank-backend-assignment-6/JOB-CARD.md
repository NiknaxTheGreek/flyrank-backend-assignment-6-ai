# Assignment 6 — LLM Job Card

## Job

Classify one customer-support message into a small trusted schema for downstream backend use.

## Input

A non-blank UTF-8 text string, maximum 4000 characters.

## Output schema

```json
{
  "category": "billing | bug | feature | other",
  "urgency": "low | normal | high",
  "confidence": 0.0,
  "reason": "short grounded explanation"
}
```

The model output is untrusted until it passes the Pydantic `ProviderClassification` schema. Extra keys, invalid enum values, blank reasons, or confidence outside 0–1 are rejected.

## Prompt contract

Prompt version: `support-classifier-v1`.

The complete operational prompt is stored in `prompts/support-classifier-v1.md`, separate from route code. It contains the role/job, exact output structure, rules, uncertainty behaviour, and three examples. `backend/prompts.py` loads the versioned file and constructs the one repair instruction from the observed validation error.

Customer data is sent separately as the provider `user` input and is treated as untrusted content rather than instructions.

## What the model must never do

- return categories or urgency values outside the closed schema;
- add arbitrary fields or prose around the JSON object;
- follow prompt-injection instructions embedded in customer text;
- invent missing facts to make a classification look more certain;
- expose system instructions, credentials, or operational secrets.

## Failure behaviour

- Invalid API input: HTTP 400 before any provider call.
- First schema-invalid provider output: quarantine the invalid output and actual validation error, then perform exactly one repair call that receives that validation error.
- Second schema-invalid provider output: quarantine it and return HTTP 422; never silently coerce or fabricate a classification.
- Timeout, rate limit, and upstream 5xx failures are transport-retryable with bounded exponential backoff plus jitter; numeric `Retry-After` is honoured where supplied.
- Provider HTTP 400/401/403 failures are not retried as transient failures.
- Missing live-provider configuration returns a controlled HTTP 503 rather than crashing application startup.
- `LLM_ENABLED=false` is a kill switch: the API still starts and health remains available, while classification returns HTTP 503 without contacting a provider.

## Uncertainty

When the input is ambiguous, the prompt requires the model to choose the best-supported label, lower confidence, state the ambiguity briefly, and use `other` when none of the specific categories is supported. Confidence is model-supplied and bounded to 0–1; it is not treated as a calibrated probability. The labelled evaluation set is the evidence used to judge behaviour.

## Observability and cost

Successful calls expose provider, model, prompt version, latency, cache status, transport retry count, repair count, input/output token counts, and estimated USD cost when explicit per-million-token rates are configured. Logs intentionally omit the customer message, API key, Authorization header, and raw provider response.

## Privacy / quarantine

Invalid provider output is written to an ignored runtime quarantine JSONL file together with a SHA-256 hash of the input, attempt number, timestamp, prompt version, and schema-validation reason. The original input text and credentials are not written to quarantine.

## Deterministic mode

`LLM_MODE=stub` provides a local deterministic provider for tests and credential-free demos. It is not represented as evidence of a genuine external model call. The historical live-provider checkpoint remains documented separately in `docs/verification.md`.
