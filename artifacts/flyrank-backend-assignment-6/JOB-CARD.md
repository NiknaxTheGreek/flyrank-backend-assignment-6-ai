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

The exact system and repair prompts are code-versioned in `backend/prompts.py`. Prompt changes must increment the version so evaluations and production observations can be tied to the prompt that produced them.

## Failure behaviour

- Invalid API input: HTTP 400.
- First schema-invalid provider output: quarantine the invalid output and perform exactly one repair call.
- Second schema-invalid provider output: quarantine it and return HTTP 422; never silently coerce or fabricate a classification.
- Timeout, rate limit, and upstream 5xx-style failures are transport-retryable with bounded exponential backoff.
- Request-rejected/client failures are not retried.
- Missing live-provider configuration returns a controlled provider error.
- `LLM_ENABLED=false` is a kill switch: the API still starts and health remains available, while classification returns HTTP 503 without contacting a provider.

## Uncertainty

The `confidence` field is model-supplied and bounded to 0–1; it is not treated as calibrated probability. The labelled evaluation set is the evidence used to judge classification behaviour.

## Observability and cost

Successful calls expose provider, model, prompt version, latency, cache status, transport retry count, repair flag, input/output token counts, and estimated USD cost when explicit per-million-token rates are configured. Logs intentionally omit the customer message, API key, Authorization header, and raw provider response.

## Privacy / quarantine

Invalid provider output is written to an ignored runtime quarantine JSONL file together with a SHA-256 hash of the input, attempt number, timestamp, and prompt version. The original input text and credentials are not written to quarantine.

## Deterministic mode

`LLM_MODE=stub` provides a local deterministic provider for tests and credential-free demos. It is not represented as evidence of a genuine external model call. The historical live-provider checkpoint remains documented separately in `docs/verification.md`.
