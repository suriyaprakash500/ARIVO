"""FastAPI application factory for ARIVO."""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from arivo.api.routes import router as api_router
from arivo.api.websocket import router as ws_router
from arivo.config import settings

_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(
        title="ARIVO",
        description="Agentic Regulatory Intelligence & Variation Orchestrator",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(api_router)
    app.include_router(ws_router)

    # Static files
    static_dir = _FRONTEND_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Templates
    templates_dir = _FRONTEND_DIR / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("dashboard.html", {"request": request})

    @app.get("/pipeline/{run_id}", response_class=HTMLResponse)
    async def pipeline_view(request: Request, run_id: str) -> HTMLResponse:
        return templates.TemplateResponse("pipeline.html", {"request": request, "run_id": run_id})

    @app.get("/review/{run_id}", response_class=HTMLResponse)
    async def review_view(request: Request, run_id: str) -> HTMLResponse:
        return templates.TemplateResponse("review.html", {"request": request, "run_id": run_id})

    @app.get("/audit/{run_id}", response_class=HTMLResponse)
    async def audit_view(request: Request, run_id: str) -> HTMLResponse:
        return templates.TemplateResponse("audit.html", {"request": request, "run_id": run_id})

    return app


app = create_app()


def main() -> None:
    uvicorn.run(
        "arivo.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
