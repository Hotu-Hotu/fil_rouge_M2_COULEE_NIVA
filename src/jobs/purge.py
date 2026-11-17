"""Suppression des donnees arrivees au bout de leur duree de conservation (docs/decisions.md)."""

import asyncio
import shutil
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.jobs.config import jobs_settings
from src.jobs.constants import JobStatus
from src.jobs.models import Job
from src.jobs.utils import job_dir, output_dir
from src.utils import utcnow


async def purge_expired_data(session: AsyncSession, now=None) -> tuple[int, int]:
    """Renvoie le nombre de traitements dont les resultats, puis tout le contenu, ont ete supprimes.

    Les lignes restent en base, sans contenu, pour que les statistiques restent justes.
    """
    now = now or utcnow()

    # 1. resultats utilisateur : disponibles dans la journee seulement
    user_limit = now - timedelta(hours=jobs_settings.USER_RETENTION_HOURS)
    expired = await session.scalars(
        select(Job).where(Job.finished_at < user_limit, Job.files_deleted_at.is_(None))
    )
    expired_count = 0
    for job in expired:
        await asyncio.to_thread(shutil.rmtree, output_dir(job.id), True)
        job.files_deleted_at = now
        expired_count += 1

    # 2. fichier recu et transcription : gardes pour les data scientists, puis supprimes
    dataset_limit = now - timedelta(days=jobs_settings.DATASET_RETENTION_DAYS)
    old = await session.scalars(
        select(Job).where(
            Job.created_at < dataset_limit,
            Job.purged_at.is_(None),
            Job.status.in_([JobStatus.DONE, JobStatus.FAILED]),
        )
    )
    purged_count = 0
    for job in old:
        await asyncio.to_thread(shutil.rmtree, job_dir(job.id), True)
        job.transcript_text = None
        job.files_deleted_at = job.files_deleted_at or now
        job.purged_at = now
        purged_count += 1

    await session.commit()
    return expired_count, purged_count
