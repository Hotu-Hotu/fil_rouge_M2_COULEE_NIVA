"""Validations des routes : chaque route recoit un objet deja verifie."""

from typing import Annotated

from fastapi import Depends, Form, Request, UploadFile

from src.exceptions import BadRequest
from src.jobs.exceptions import JobFileNotFound, JobNotFound
from src.jobs.service import Job, JobQueue
from src.transcription.models import OutputFormat
from src.transcription.pipeline import InvalidRequest, check_format


async def get_queue(request: Request) -> JobQueue:
    return request.app.state.queue


Queue = Annotated[JobQueue, Depends(get_queue)]


async def valid_upload(file: UploadFile, output_format: Annotated[OutputFormat, Form()]):
    """Refuse une extension ou un format impossible avant de recevoir tout le fichier."""
    try:
        check_format(file.filename or "", output_format)
    except InvalidRequest as error:
        raise BadRequest(str(error)) from error
    return file, output_format


async def valid_job_id(job_id: str, queue: Queue) -> Job:
    job = queue.get(job_id)
    if job is None:
        raise JobNotFound()
    return job


async def valid_job_file(name: str, job: Annotated[Job, Depends(valid_job_id)]):
    """Chemin d'un fichier produit par le traitement. Aucun autre chemin n'est servi."""
    if name not in job.files:
        raise JobFileNotFound()
    return job.output_dir / name
