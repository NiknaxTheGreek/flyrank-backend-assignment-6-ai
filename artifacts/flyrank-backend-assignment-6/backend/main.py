"""Application entry point for POST /llm/classify."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .models import ClassificationResult, ErrorResponse, SupportMessageInput
from .providers import ProviderFailure, ProviderOutputError, StubProvider, build_provider
from .service import ClassifierService
from .settings import Settings


def create_app(settings: Settings | None = None, service: ClassifierService | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    if service is not None:
        active_service = service
    elif not active_settings.llm_enabled:
        # The kill switch must allow the API to start even when a live provider
        # is intentionally unconfigured. classify() will return the controlled
        # llm_disabled response before this inert provider is ever called.
        active_service = ClassifierService(active_settings, StubProvider())
    else:
        active_service = ClassifierService(active_settings, build_provider(active_settings))

    app = FastAPI(title="FlyRank Assignment 6", version="1.1.0")
    app.state.classifier = active_service

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(error="invalid request body", code="invalid_input").model_dump(),
        )

    @app.exception_handler(ProviderOutputError)
    async def invalid_output(_: Request, __: ProviderOutputError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="provider output remained invalid after one repair attempt",
                code="invalid_provider_output",
            ).model_dump(),
        )

    @app.exception_handler(ProviderFailure)
    async def provider_error(_: Request, exc: ProviderFailure) -> JSONResponse:
        status, message, code = {
            "disabled": (503, "LLM classification is currently disabled", "llm_disabled"),
            "timeout": (504, "provider timed out", "provider_timeout"),
            "rate_limited": (429, "provider rate limit reached", "provider_rate_limited"),
            "upstream": (503, "provider is temporarily unavailable", "provider_unavailable"),
            "request_rejected": (502, "provider rejected the request", "provider_rejected"),
            "misconfigured": (503, "LLM provider is not configured", "provider_misconfigured"),
        }.get(exc.kind, (502, "provider request failed", "provider_failure"))
        return JSONResponse(
            status_code=status,
            content=ErrorResponse(error=message, code=code).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error="unexpected service failure", code="unexpected_failure").model_dump(),
        )

    @app.get("/healthz")
    @app.get("/api/llm/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/llm/classify",
        response_model=ClassificationResult,
        responses={
            400: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            429: {"model": ErrorResponse},
            502: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    @app.post("/api/llm/classify", response_model=ClassificationResult, include_in_schema=False)
    async def classify(message: SupportMessageInput) -> ClassificationResult:
        return await app.state.classifier.classify(message.text)

    return app


app = create_app()
