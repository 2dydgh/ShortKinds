"""
FastAPI Backend for Short Kinds
Modern web application backend with async support
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Add parent directory to path to import existing modules
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.api import news, media, tasks

# Initialize FastAPI app
app = FastAPI(
    title="Short Kinds API",
    description="News summarization, image generation, and TTS API",
    version="2.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(news.router, prefix="/api", tags=["news"])
app.include_router(media.router, prefix="/api", tags=["media"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])

# Serve static files (outputs folder)
outputs_dir = ROOT / "outputs"
outputs_dir.mkdir(exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

# Serve assets folder (for demo videos, images, etc.)
assets_dir = ROOT / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# Serve frontend
frontend_dir = ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.get("/")
async def root():
    """Serve the frontend HTML"""
    frontend_file = frontend_dir / "index.html"
    if frontend_file.exists():
        return FileResponse(frontend_file)
    return {"message": "Short Kinds API", "docs": "/docs"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
