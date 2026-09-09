"""FastAPI surface. Caspian remains the comms core; HTTP hosts health, the
hosted-gateway push route, and the student REST API (same Core Agent)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app import config
from backend.app.api import auth as auth_routes
from backend.app.api import resources
from backend.app.comms.client import build_caspian_app
from backend.app.db import init_db

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CampusOps", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_routes.router)
app.include_router(resources.student_router)
app.include_router(resources.tt_router)
app.include_router(resources.email_router)
app.include_router(resources.docs_router)
app.include_router(resources.plan_router)
app.include_router(resources.notif_router)
app.include_router(resources.chat_router)
app.include_router(resources.integr_router)

_cx = None


def get_cx():
    global _cx
    if _cx is None:
        if not config.CASPIAN_API_KEY or not config.CAMPUSOPS_MAILBOX:
            raise HTTPException(
                status_code=503,
                detail="Messaging not configured (CASPIAN_API_KEY/CAMPUSOPS_MAILBOX).",
            )
        _cx = build_caspian_app(
            api_key=config.CASPIAN_API_KEY,
            mailbox=config.CAMPUSOPS_MAILBOX,
            base_url=config.CASPIAN_BASE_URL,
        )
    return _cx


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "campusops"}


@app.post("/caspian/gateway")
async def caspian_gateway(request: Request) -> JSONResponse:
    """Hosted push endpoint (used instead of `runner` polling when configured)."""
    cx = get_cx()
    body = await request.body()
    results = cx.handle("gateway", bytes(body), dict(request.headers))
    ok = sum(1 for r in results if r.is_ok)
    return JSONResponse({"received": len(results), "ok": ok})
