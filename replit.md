# FlyRank Assignment 6

Customer-support classification behind a safe FastAPI LLM adapter, with a browser console for inspecting validated results and operational metadata.

## Run & Operate

- `PYTHONPATH=artifacts/flyrank-backend-assignment-6 uv run python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` — run the FastAPI service
- `pnpm --filter @workspace/flyrank-backend-assignment-6 run dev` — run the browser console
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `PYTHONPATH=artifacts/flyrank-backend-assignment-6 uv run pytest artifacts/flyrank-backend-assignment-6/backend/tests -q` — run service tests
- `PYTHONPATH=artifacts/flyrank-backend-assignment-6 uv run python -m backend.eval_runner` — run the labeled stub evaluation
- `uv pip check` — audit Python package compatibility

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Python FastAPI + Uvicorn
- Provider: deterministic stub by default; optional OpenAI Responses adapter
- Validation: Pydantic 2
- API codegen: Orval (from OpenAPI spec)
- Frontend: React + Vite + TanStack Query

## Where things live

- `artifacts/flyrank-backend-assignment-6/backend/` — FastAPI app, provider adapters, service orchestration, tests, and evaluation data
- `artifacts/flyrank-backend-assignment-6/src/` — browser console
- `lib/api-spec/openapi.yaml` — generated frontend contract source of truth
- `artifacts/flyrank-backend-assignment-6/docs/` — requirements audit, verification evidence, and source-gap notes

## Architecture decisions

- Provider output is parsed and validated with a strict Pydantic model before it can become an API response.
- The LLM kill switch is checked before cache access, so disabling the provider is deterministic and immediate.
- Cache keys are SHA-256 digests of normalized input text; cache metadata remains visible without exposing content or credentials.
- Only timeout, 429, and upstream 5xx failures retry, with a bounded exponential delay.

## Product

Users can submit support text, inspect category/urgency/confidence/reason, and see provider, model, latency, cache, retry, and token metadata. They can run credential-free stub mode or configure the optional OpenAI Responses adapter entirely through environment variables.

## User preferences

The live OpenAI checkpoint must not be claimed unless an authorized call actually succeeds. The human-vs-AI S4 rematch remains pending until a separate human Assignment 6 is provided.

## Gotchas

- Use `LLM_MODE=stub` for local tests and demos; never place API keys in source or committed env files.
- Run API codegen after changing `lib/api-spec/openapi.yaml`.
- The FastAPI service has both `/llm/classify` (assignment contract) and `/api/llm/classify` (routed browser endpoint).

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
