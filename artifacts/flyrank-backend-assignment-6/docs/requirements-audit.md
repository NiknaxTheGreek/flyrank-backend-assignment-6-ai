# Requirements audit

| Requirement | Evidence |
| --- | --- |
| `POST /llm/classify` input/output contract | `backend/main.py`, `backend/models.py` |
| Structured output treated as untrusted | `ProviderClassification.model_validate_json` |
| Restricted category, urgency, confidence bounds | Pydantic enums and `Field(ge=0, le=1)` |
| OpenAI-compatible Responses adapter via environment only | `OpenAIResponsesProvider`, `.env.example`; supports direct OpenAI and Replit AI Integrations proxy credentials |
| Stub and kill switch | `LLM_MODE=stub`, `LLM_ENABLED=false`, test coverage |
| 30-second timeout and selective retry | `Settings`, `ClassifierService._is_retryable` |
| Error mapping without secret leaks | FastAPI exception handlers and hygiene test |
| In-memory duplicate-input cache and operational metadata | `ClassifierService`, response metadata |
| Labeled evaluation with observed scores | `backend/eval_cases.json`, `eval_runner.py`, `eval_results.json` |
| Genuine external provider checkpoint | `docs/verification.md` records a real managed-provider `POST /llm/classify` response, latency, cache state, and token usage |
| S4 human-vs-AI rematch | Explicitly pending; no human assignment inspected |