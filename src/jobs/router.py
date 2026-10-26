from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from src.exceptions import PayloadTooLarge
from src.jobs.constants import UPLOAD_CHUNK_SIZE
from src.jobs.dependencies import Queue, valid_job_file, valid_job_id, valid_upload
from src.jobs.schemas import JobResponse
from src.jobs.service import Job
from src.transcription.config import transcription_settings
from src.transcription.models import OutputFormat
from src.transcription.pipeline import InvalidRequest, check_size

router = APIRouter(prefix="/jobs", tags=["Traitements"])

NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"description": "Traitement ou fichier introuvable"}}


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobResponse,
    summary="Envoyer un fichier a transcrire",
    description="Recoit un .mp4 ou un .wav et met son traitement en file d'attente. "
    "Formats : burned et track (video uniquement), subtitles, text.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Extension ou format non disponible"},
        status.HTTP_413_CONTENT_TOO_LARGE: {"description": "Fichier trop volumineux"},
    },
)
async def create_job(
    upload: Annotated[tuple[UploadFile, OutputFormat], Depends(valid_upload)],
    queue: Queue,
):
    file, output_format = upload
    job = queue.new_job(file.filename, output_format)

    # copie par morceaux : on s'arrete des que le fichier depasse la taille maximale
    max_bytes = transcription_settings.MAX_SIZE_MB * 1_000_000
    size = 0
    with job.input_path.open("wb") as destination:
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            size += len(chunk)
            if size > max_bytes:
                break
            # l'ecriture disque est bloquante : on la sort de la boucle d'evenements
            await run_in_threadpool(destination.write, chunk)
    try:
        job.warnings = check_size(size)
    except InvalidRequest as error:
        queue.discard(job)
        raise PayloadTooLarge(str(error)) from error

    queue.submit(job)
    return job.to_response()


@router.get("/{job_id}", response_model=JobResponse, summary="Suivre un traitement", responses=NOT_FOUND)
async def read_job(job: Annotated[Job, Depends(valid_job_id)]):
    return job.to_response()


@router.get(
    "/{job_id}/files/{name}",
    response_class=FileResponse,
    summary="Telecharger un resultat",
    responses=NOT_FOUND,
)
async def download_file(path: Annotated[Path, Depends(valid_job_file)]):
    return FileResponse(path, filename=path.name)
