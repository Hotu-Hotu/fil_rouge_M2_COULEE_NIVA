"""Point d'entree de l'API. Lancement : uvicorn src.main:app

L'API ne charge pas le modele : elle enregistre les traitements en base, et le worker
(python -m src.jobs.worker) les execute.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.admin.router import router as admin_router
from src.config import settings
from src.database import engine
from src.jobs.router import router as jobs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


# la documentation n'est exposee qu'en local et en recette
app = FastAPI(
    title="Transcription",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    openapi_url="/openapi.json" if settings.ENVIRONMENT.shows_docs else None,
)
app.include_router(jobs_router)
app.include_router(admin_router)


@app.get("/health", tags=["Supervision"], summary="Verifier que l'API repond")
async def health():
    return {"status": "ok"}
