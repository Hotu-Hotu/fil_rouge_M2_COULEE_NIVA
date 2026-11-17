import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from src.auth.dependencies import CurrentUser
from src.database import Session
from src.exceptions import PayloadTooLarge
from src.jobs import service
from src.jobs.constants import UPLOAD_CHUNK_SIZE
from src.jobs.dependencies import valid_job_file, valid_owned_job, valid_upload
from src.jobs.models import Job
from src.jobs.schemas import JobResponse
from src.jobs.utils import input_path, job_dir
from src.transcription.config import transcription_settings
from src.transcription.models import OutputFormat
from src.transcription.pipeline import InvalidRequest, check_size

router = APIRouter(prefix="/jobs", tags=["Traitements"])

UNAUTHORIZED = {status.HTTP_401_UNAUTHORIZED: {"description": "Cle d'API absente ou invalide"}}
NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"description": "Traitement ou fichier introuvable"}}


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobResponse,
    summary="Envoyer un fichier a transcrire",
    description="Recoit un .mp4 ou un .wav et met son traitement en file d'attente. "
    "Formats : burned et track (video uniquement), subtitles, text.",
    responses={
        **UNAUTHORIZED,
        status.HTTP_400_BAD_REQUEST: {"description": "Extension ou format non disponible"},
        status.HTTP_413_CONTENT_TOO_LARGE: {"description": "Fichier trop volumineux"},
    },
)
async def create_job(
    upload: Annotated[tuple[UploadFile, OutputFormat], Depends(valid_upload)],
    user: CurrentUser,
    session: Session,
):
    file, output_format = upload
    job_id = service.new_job_id()
    destination_path = input_path(job_id, file.filename)
    destination_path.parent.mkdir(parents=True)

    # copie par morceaux : on s'arrete des que le fichier depasse la taille maximale
    max_bytes = transcription_settings.MAX_SIZE_MB * 1_000_000
    size = 0
    with destination_path.open("wb") as destination:
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            size += len(chunk)
            if size > max_bytes:
                break
            # l'ecriture disque est bloquante : on la sort de la boucle d'evenements
            await run_in_threadpool(destination.write, chunk)
    try:
        warnings = check_size(size)
    except InvalidRequest as error:
        await run_in_threadpool(shutil.rmtree, job_dir(job_id), True)
        raise PayloadTooLarge(str(error)) from error

    # le traitement n'entre dans la file qu'une fois le fichier complet sur le disque
    job = await service.create_job(session, job_id, user, file.filename, output_format, warnings)
    return JobResponse.from_job(job)


@router.get("", response_model=list[JobResponse], summary="Lister mes traitements", responses=UNAUTHORIZED)
async def list_jobs(
    user: CurrentUser,
    session: Session,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return [JobResponse.from_job(job) for job in await service.list_user_jobs(session, user, limit, offset)]


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Suivre un traitement",
    responses={**UNAUTHORIZED, **NOT_FOUND},
)
async def read_job(job: Annotated[Job, Depends(valid_owned_job)]):
    return JobResponse.from_job(job)


@router.get(
    "/{job_id}/files/{name}",
    response_class=FileResponse,
    summary="Telecharger un resultat",
    responses={
        **UNAUTHORIZED,
        **NOT_FOUND,
        status.HTTP_410_GONE: {"description": "Resultat supprime apres la journee de conservation"},
    },
)
async def download_file(path: Annotated[Path, Depends(valid_job_file)]):
    return FileResponse(path, filename=path.name)
