"""FastAPI application — serves both the API and the web frontend."""

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.api.routes import search, reports, analysis
from src.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Library",
    description="Policy report corpus: search, analyze, and synthesize across World Bank, UN, IMF, and think tank publications.",
    version="0.1.0",
    lifespan=lifespan,
)

# API routes
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])

# Serve frontend static files
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
app.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
app.mount("/js", StaticFiles(directory=frontend_dir / "js"), name="js")


@app.get("/")
async def serve_frontend():
    return FileResponse(frontend_dir / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
