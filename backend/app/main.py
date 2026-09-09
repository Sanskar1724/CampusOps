"""FastAPI surface. Caspian remains the comms core; HTTP only hosts health
checks today plus the hosted-gateway push route for later use."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.app import config
from backend.app.comms.client import build_caspian_app

app = FastAPI(title="CampusOps", version="0.1.0")

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
