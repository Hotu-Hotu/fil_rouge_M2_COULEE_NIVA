"""Traitements en base. La table job sert aussi de file d'attente : l'API y ajoute les
traitements, les workers (src/jobs/worker.py) viennent les y prendre.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import UserAccount
from src.jobs.constants import JobStatus
from src.jobs.models import Job
from src.transcription.models import OutputFormat
from src.utils import utcnow


def new_job_id():
    return uuid.uuid4().hex


async def create_job(
    session: AsyncSession, job_id, user: UserAccount, filename, output_format: OutputFormat, warnings
) -> Job:
    job = Job(id=job_id, user_id=user.id, filename=filename, output_format=output_format, warnings=warnings)
    session.add(job)
    await session.commit()
    return job


async def get_job(session: AsyncSession, job_id) -> Job | None:
    return await session.get(Job, job_id)


async def list_user_jobs(session: AsyncSession, user: UserAccount, limit, offset) -> list[Job]:
    query = (
        select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(limit).offset(offset)
    )
    return list(await session.scalars(query))


async def claim_next_job(session: AsyncSession, worker_name) -> Job | None:
    """Prend le plus ancien traitement en attente. Sur si plusieurs workers tournent en meme temps."""
    while True:
        job_id = await session.scalar(
            select(Job.id).where(Job.status == JobStatus.QUEUED).order_by(Job.created_at).limit(1)
        )
        if job_id is None:
            return None
        # mise a jour conditionnelle : si un autre worker a pris ce traitement entre-temps,
        # aucune ligne n'est modifiee et on passe au suivant
        claimed = await session.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.QUEUED)
            .values(status=JobStatus.RUNNING, started_at=utcnow(), worker_name=worker_name)
        )
        await session.commit()
        if claimed.rowcount == 1:
            return await session.get(Job, job_id, populate_existing=True)


async def fail_interrupted_jobs(session: AsyncSession, worker_name) -> int:
    """Au demarrage d'un worker : ses traitements restes en cours ont ete coupes par un arret ou un crash."""
    result = await session.execute(
        update(Job)
        .where(Job.status == JobStatus.RUNNING, Job.worker_name == worker_name)
        .values(
            status=JobStatus.FAILED,
            finished_at=utcnow(),
            error="Traitement interrompu par un arret du service : relancez-le",
        )
    )
    await session.commit()
    return result.rowcount
