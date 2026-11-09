# SPDX-License-Identifier: Apache-2.0
import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from overlord import __version__
from overlord.config import Settings
from overlord.logging import configure_logging
from overlord.models import (
    Acknowledgement,
    CommandPoll,
    Control,
    IngestResult,
    Observation,
    SessionCreate,
)
from overlord.providers import MockProvider, Provider
from overlord.response import Responses
from overlord.storage import Conflict, Store, UnknownSession

log = logging.getLogger("overlord.api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    store = Store(settings.database_path, settings.response_cooldown_seconds)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        store.initialize()
        log.info("service_started")
        yield
        log.info("service_stopped")

    app = FastAPI(title="OVERLORD Director", version=__version__, lifespan=lifespan)
    provider: Provider = MockProvider()
    app.state.provider = provider

    @app.exception_handler(Conflict)
    async def conflict(request: Request, exc: Conflict) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(UnknownSession)
    async def unknown(request: Request, exc: UnknownSession) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Unknown session"})

    @app.exception_handler(sqlite3.Error)
    async def unavailable(request: Request, exc: sqlite3.Error) -> JSONResponse:
        log.error("storage_unavailable")
        return JSONResponse(status_code=503, content={"detail": "Storage unavailable"})

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Do not echo raw input or Pydantic's input field (could contain sensitive text).
        errors = [{"loc": e["loc"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.get("/health")
    def health() -> dict[str, str]:
        store.health()
        return {"status": "ok"}

    @app.get("/version")
    def version() -> dict[str, str]:
        return {
            "service": "overlord-director",
            "version": __version__,
            "protocol_version": "1.0",
            "provider": settings.provider,
        }

    @app.post("/v1/sessions", response_model=SessionCreate, status_code=201)
    def create_session(session: SessionCreate) -> SessionCreate:
        store.create_session(session)
        return session

    @app.get("/v1/sessions", response_model=list[SessionCreate])
    def sessions(limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[SessionCreate]:
        return store.sessions(limit)

    @app.post("/v1/observations", response_model=IngestResult, status_code=201)
    def ingest(observation: Observation, response: Response) -> IngestResult:
        recorded = store.record(observation)
        status: Literal["recorded", "duplicate"] = "recorded" if recorded else "duplicate"
        if not recorded:
            response.status_code = 200
        log.info(
            "observation_ingested",
            extra={
                "event_id": observation.event_id,
                "session_id": observation.session_id,
                "event_type": observation.event_type,
                "status": status,
            },
        )
        # Recording is deliberately independent of provider availability or latency.
        return IngestResult(event_id=observation.event_id, status=status)

    @app.get("/v1/sessions/{session_id}/observations", response_model=list[Observation])
    def observations(
        session_id: UUID,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> list[Observation]:
        return store.observations(session_id, offset, limit)

    responses = Responses(store)

    @app.get("/v1/sessions/{session_id}/responses")
    def response_status(session_id: UUID) -> dict[str, Any]:
        return responses.inspect(session_id)

    @app.put("/v1/sessions/{session_id}/control", response_model=Control)
    def response_control(session_id: UUID, mode: Control) -> Control:
        return responses.set_control(session_id, mode)

    @app.post("/v1/commands/poll")
    def command_poll(request: CommandPoll) -> list[Any]:
        return responses.poll(request.session_id)

    @app.post("/v1/acknowledgements")
    def acknowledge(ack: Acknowledgement) -> dict[str, str]:
        responses.acknowledge(ack)
        return {"status": "recorded"}

    return app
