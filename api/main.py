import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import CORS_ORIGINS
from routers import sessions, predict, baseline, suggestions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Burnout Copilot API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

app.include_router(sessions.router)
app.include_router(predict.router)
app.include_router(baseline.router)
app.include_router(suggestions.router)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"status": "ok", "message": "Burnout Copilot API is running"}