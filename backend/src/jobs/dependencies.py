"""Validations des routes : chaque route recoit un objet deja verifie."""

from typing import Annotated

from fastapi import Depends, Form, UploadFile

from src.auth.dependencies import CurrentUser
from src.database import Session
from src.exceptions import BadRequest
from src.jobs.exceptions import JobFileNotFound, JobFilesExpired, JobNotFound
from src.jobs.models import Job
from src.jobs.service import get_job
from src.jobs.utils import output_dir
from src.transcription.models import OutputFormat
from src.transcription.pipeline import InvalidRequest, check_format


async def valid_upload(file: UploadFile, output_format: Annotated[OutputFormat, Form()]):
    """Refuse une extension ou un format impossible avant de recevoir tout le fichier."""
    try:
        check_format(file.filename or "", output_format)
    except InvalidRequest as error:
        raise BadRequest(str(error)) from error
    return file, output_format


async def valid_owned_job(job_id: str, user: CurrentUser, session: Session) -> Job:
    """Un utilisateur ne voit que ses traitements. Ceux des autres sont introuvables pour lui."""
    job = await get_job(session, job_id)
    if job is None or job.user_id != user.id:
        raise JobNotFound()
    return job


async def valid_job_file(name: str, job: Annotated[Job, Depends(valid_owned_job)]):
    """Chemin d'un fichier produit par le traitement. Aucun autre chemin n'est servi."""
    if name not in job.files:
        raise JobFileNotFound()
    if job.files_deleted_at is not None:
        raise JobFilesExpired()
    return output_dir(job.id) / name
