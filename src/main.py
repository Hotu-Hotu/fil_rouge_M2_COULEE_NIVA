"""Point d'entree de l'API. Lancement : uvicorn src.main:app"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import settings
from src.jobs.config import jobs_settings
from src.jobs.router import router as jobs_router
from src.jobs.service import JobQueue
from src.transcription.config import transcription_settings
from src.transcription.transcribers import get_transcriber


@asynccontextmanager
async def lifespan(app: FastAPI):
    # le modele est charge une seule fois, au demarrage de l'API
    transcriber = get_transcriber(transcription_settings.TRANSCRIBER, transcription_settings.MODEL_NAME)
    app.state.queue = JobQueue(transcriber, jobs_settings.DATA_DIR)
    yield
    app.state.queue.shutdown()


# la documentation n'est exposee qu'en local et en recette
app = FastAPI(
    title="Transcription",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    openapi_url="/openapi.json" if settings.ENVIRONMENT.shows_docs else None,
)
app.include_router(jobs_router)


@app.get("/health", tags=["Supervision"], summary="Verifier que l'API repond")
async def health():
    return {"status": "ok"}
