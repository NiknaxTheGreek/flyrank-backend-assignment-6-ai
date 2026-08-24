# Assignment 6 Requirements Audit

Authoritative source: recovered S3 — **Assignment 6: Connect to an AI API / Put an LLM Behind Your API**.

| S3 requirement | Current implementation / evidence | Status |
| --- | --- | --- |
| Narrow, closed, human-gradeable LLM job | Support-message triage into four categories + three urgency levels | PASS |
| Pre-coding job definition | `JOB-CARD.md` defines job, input, output, prohibited behaviour, uncertainty and failure handling | PASS |
| `POST /llm/classify` input/output contract | `backend/main.py`, `backend/models.py` | PASS |
| Invalid input rejected before provider call | strict Pydantic request model; blank/extra-field tests return HTTP 400 | PASS |
| Stub mode | `LLM_MODE=stub` deterministic `StubProvider`; HTTP gate exercises it | PASS |
| Versioned prompt stored outside route code | `prompts/support-classifier-v1.md`, loaded by `backend/prompts.py` | PASS |
| Prompt contains role/job | section 1 of versioned prompt | PASS |
| Prompt contains exact output structure | section 2 + strict JSON Schema provider payload | PASS |
| Prompt contains rules | section 3 | PASS |
| Prompt contains uncertainty behaviour | section 4 | PASS |
| Prompt contains 2–3 examples | section 5 contains three: normal, ambiguous, hostile/prompt-injection | PASS |
| User data separate from system instructions | provider sends system prompt and customer text as separate system/user items; tested | PASS |
| Low temperature | OpenAI-compatible payload sets `temperature: 0`; tested | PASS |
| Treat model output as untrusted | `ProviderClassification.model_validate_json()` is the trust boundary | PASS |
| Remove/avoid output wrapping artifacts | strict JSON-only structured-output path rejects non-schema text rather than trusting it | PASS |
| Exactly one repair retry | first invalid output causes one `provider.repair()` only; repair count is bounded 0–1 | PASS |
| Repair uses observed validation error | `ProviderOutputError.validation_error` is passed into `build_repair_prompt()`; dedicated test | PASS |
| Second invalid output returns HTTP 422 | FastAPI error mapping + deterministic two-invalid-output test | PASS |
| Quarantine unrecoverable/invalid output context | ignored JSONL stores input hash, prompt version, attempt, raw invalid output and validation reason; original customer text not stored | PASS |
| Secure provider configuration | environment variables / managed-secret injection; `.env.example` contains no credential | PASS |
| Genuine provider evidence | `docs/verification.md` preserves executed 2026-08-22 managed OpenAI-compatible request | PASS |
| Timeout <=60 seconds | default 30 s; environment value clamped to 60 s; tested | PASS |
| Retry timeout / 429 / 5xx | only `timeout`, `rate_limited`, `upstream` are retryable | PASS |
| Do not retry 400 / 401 / 403 | request/auth rejection tests prove one provider call only | PASS |
| Exponential backoff + jitter | `ClassifierService._call_with_retries()`; deterministic injected-jitter test | PASS |
| Honour `Retry-After` where available | provider parses numeric header and service honours it; 429 test | PASS |
| SDK retry decision explicit | direct `httpx` is used, so there is no second SDK retry layer; README documents this | PASS |
| Wrong credentials fail as auth error | 401/403 map to controlled `provider_auth_failed`, non-retryable | PASS |
| Missing live credential does not crash startup | `MisconfiguredProvider` permits startup and returns controlled 503; tested | PASS |
| Kill switch | `LLM_ENABLED=false` returns controlled 503 without provider work and permits startup | PASS |
| Logging: prompt/model/tokens/duration/repair count | `backend/service.py` logs operational metadata and cost without customer text or credentials; tested | PASS |
| No raw unvalidated model output to caller | invalid provider outputs are quarantined; caller receives sanitized 422 | PASS |
| Token/cost evidence | provider metadata includes token counts; configured-rate calculation tested; README includes direct-list-price example | PASS |
| 10,000-request/day cost estimate | README uses observed 130/31-token genuine checkpoint + official 2026-08-24 GPT-4.1 mini direct API list pricing to calculate ~$1.016/day | PASS |
| At least eight labelled eval cases | 12 labelled cases | PASS |
| Actual eval score/date/prompt/provider/model | README + `backend/eval_results.json`; current measured 11/12 category, 12/12 urgency, 11/12 joint | PASS |
| Identified improvement | README retains the `bug-access` miss and names it as a future improvement target | PASS |
| Valid and invalid curl examples | README includes both | PASS |
| Provider/environment switching instructions | README + `.env.example` | PASS |
| Root submission discoverability | root `README.md` points directly to the assignment artifact | PASS |
| Current GitHub Actions checkpoint | Run `32710153130`: compile PASS, **24 tests PASS**, labelled 12-case eval PASS, Uvicorn/stub HTTP gate PASS | PASS |
| AI Rematch comparison | separate project-required S4 stage after the human version exists; not represented as complete here | PENDING HUMAN VERSION |

## Current measured checkpoint

GitHub Actions run `32710153130` on 2026-08-24 executed the final repaired code on Python 3.13. The suite reported **24 passed, 1 non-failing TestClient deprecation warning**. The labelled deterministic evaluation remained category `11/12`, urgency `12/12`, joint `11/12`, and the actual HTTP probe printed `STUB_HTTP_GATE=PASS` with `repair_count=0`.

The genuine managed-provider checkpoint is older executed evidence and is intentionally kept distinct from current deterministic CI. No fresh paid-provider request is claimed for GitHub Actions because no provider credential is exposed to the workflow.
