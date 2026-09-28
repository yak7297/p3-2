from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import setting
from app.models import HealthResponse
from app.routes import router


app = FastAPI(title="학습시간 데이터 AI 비서 API", version="0.1.0")
origins = [
    origin.strip()
    for origin in setting(
        "ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(router)


@app.get("/health", tags=["system"], response_model=HealthResponse)
def health():
    return {
        "status": "ok",
        "storage": setting("STORAGE_BACKEND", "local"),
        "ai_mode": setting("AI_MODE", "mock"),
        "ai_configured": bool(setting("OPENAI_API_KEY")),
    }


frontend = Path(__file__).resolve().parents[1] / "frontend"
if frontend.exists():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
