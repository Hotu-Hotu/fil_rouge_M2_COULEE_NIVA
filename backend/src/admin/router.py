from typing import Annotated

from fastapi import APIRouter, Query, status

from src.admin import service
from src.admin.schemas import (
    AdminJobResponse,
    ContentAccessRequest,
    ContentAccessResponse,
    ContentResponse,
    StatsResponse,
)
from src.auth.dependencies import CurrentAdmin
from src.database import Session
from src.exceptions import Gone
from src.jobs import service as jobs_service
from src.jobs.constants import JobStatus
from src.jobs.exceptions import JobNotFound
from src.transcription.models import OutputFormat

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Cle d'API absente ou invalide"},
        status.HTTP_403_FORBIDDEN: {"description": "Acces reserve aux administrateurs"},
    },
)

Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/stats", response_model=StatsResponse, summary="Statistiques d'usage")
async def read_stats(admin: CurrentAdmin, session: Session):
    return await service.get_stats(session)


@router.get(
    "/jobs",
    response_model=list[AdminJobResponse],
    summary="Lister les traitements",
    description="Metadonnees des traitements de tous les utilisateurs, sans leur contenu.",
)
async def list_jobs(
    admin: CurrentAdmin,
    session: Session,
    status: JobStatus | None = None,
    output_format: OutputFormat | None = None,
    user_id: int | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    jobs = await service.list_jobs(session, status, output_format, user_id, limit, offset)
    return [AdminJobResponse.from_job(job) for job in jobs]


@router.post(
    "/jobs/{job_id}/content",
    response_model=ContentResponse,
    summary="Consulter le contenu d'un traitement",
    description="Necessite une autorisation legale. Chaque consultation est enregistree.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Traitement introuvable"},
        status.HTTP_410_GONE: {"description": "Contenu supprime ou jamais produit"},
    },
)
async def read_content(job_id: str, request: ContentAccessRequest, admin: CurrentAdmin, session: Session):
    job = await jobs_service.get_job(session, job_id)
    if job is None:
        raise JobNotFound()
    if job.transcript_text is None:
        raise Gone("Aucun contenu disponible : traitement non termine, echoue ou purge")
    await service.record_content_access(session, job, admin, request)
    return ContentResponse(job_id=job.id, transcript_text=job.transcript_text)


@router.get(
    "/content-accesses",
    response_model=list[ContentAccessResponse],
    summary="Journal des consultations de contenu",
)
async def list_content_accesses(admin: CurrentAdmin, session: Session, limit: Limit = 50, offset: Offset = 0):
    accesses = await service.list_content_accesses(session, limit, offset)
    return [ContentAccessResponse.from_access(access) for access in accesses]
