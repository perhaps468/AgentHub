from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.sessions import router as sessions_router
from app.api.ws import router as ws_router


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


app = FastAPI(title="AgentHub Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validation_errors_for_json(exc: RequestValidationError) -> list[dict]:
    errors = exc.errors()
    for error in errors:
        if "ctx" in error:
            error["ctx"] = {key: str(value) for key, value in error["ctx"].items()}
    return errors


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": validation_errors_for_json(exc)},
    )


@app.get("/")
def root() -> dict:
    return {
        "service": "agenthub-backend",
        "status": "ok",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict:
    return {
        "service": "agenthub-backend",
        "status": "ok",
        "timestamp": iso_now(),
    }


@app.get("/api/health")
def api_health() -> dict:
    return health()


app.include_router(sessions_router)
app.include_router(ws_router)
