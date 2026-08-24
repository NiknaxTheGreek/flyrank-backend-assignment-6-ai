# Assignment 6 Requirements Audit

| Requirement | Implementation / evidence | Status |
| --- | --- | --- |
| `POST /llm/classify` input/output contract | `backend/main.py`, `backend/models.py` | PASS |
| Define the LLM job before calling a model | `JOB-CARD.md` records job, input, schema, uncertainty and failure behaviour | PASS |
| Version the prompt | `backend/prompts.py`, metadata field `prompt_version=support-classifier-v1` | PASS |
| Treat model output as untrusted | `ProviderClassification.model_validate_json()` is the trust boundary | PASS |
| Restricted category/urgency/confidence/reason | Pydantic enums, bounds and validators | PASS |
| Exactly one repair attempt for invalid structured output | `ClassifierService.classify()` quarantines first invalid output and performs one `provider.repair()` call only | PASS |
| Still-invalid repair fails explicitly | FastAPI maps the second `ProviderOutputError` to HTTP 422 `invalid_provider_output` | PASS |
| Quarantine invalid provider output | ignored runtime JSONL contains input hash, timestamp, prompt version, attempt and invalid raw output; tests verify original input text is not stored | PASS |
| OpenAI-compatible managed/live provider | `OpenAIResponsesProvider`; direct or Replit-managed environment injection only | PASS |
| Genuine external provider evidence | Existing `docs/verification.md` records the executed Replit AI Integrations call, model, 200 result, latency and token usage without credentials | PASS |
| Finite timeout | environment-configured timeout, default 30 s | PASS |
| Selective retry with backoff | only timeout/rate-limit/upstream failures are retryable; 400/401/403 and other client failures are not | PASS |
| Stub mode | deterministic `StubProvider` for tests/credential-free demos | PASS |
| Kill switch | `LLM_ENABLED=false` returns 503 without provider work | PASS |
| Kill switch does not break startup when live provider is unconfigured | `create_app()` uses an inert provider when disabled; dedicated no-key/openai-mode test | PASS |
| Cache duplicate input | SHA-256 keyed TTL cache in `ClassifierService` | PASS |
| Safe observability | structured operational logging excludes customer text, API keys, Authorization headers and raw provider responses | PASS |
| Token and cost evidence | metadata records input/output tokens; cost is calculated only from explicit configured rates and is otherwise unasserted | PASS |
| Labelled evaluation | 12 labelled cases with generated observed results and accuracy calculations | PASS |
| Deterministic automated coverage | expanded backend suite covers API, repair, quarantine, retries, kill switch, cache, adapter, logging and cost | PASS |
| Root submission discoverability | root `README.md` points directly to the assignment artifact and verification command | PASS |
| Current GitHub Actions checkpoint | `.github/workflows/assignment-6-s3.yml` runs compile, tests, evaluation and stub HTTP probe | PENDING CURRENT RUN |
| AI Rematch comparison | deliberately separate; no human implementation is inspected or replaced here | PENDING HUMAN VERSION |

The older live-provider checkpoint remains historical executed evidence. This repair does not claim that GitHub Actions made a fresh paid/managed provider request because no provider credential is exposed to the workflow.
