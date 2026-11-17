from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.models import AdminContentAccess
from src.admin.schemas import ContentAccessRequest, StatsResponse, UsageStats
from src.auth.models import UserAccount
from src.jobs.constants import JobStatus
from src.jobs.models import Job
from src.transcription.models import OutputFormat


def _count_if(condition):
    return func.sum(case((condition, 1), else_=0))


def _done_sum(column):
    return func.sum(case((Job.status == JobStatus.DONE, column), else_=None))


def _to_stats(total, done, failed, unfinished, processing_sum, media_sum) -> UsageStats:
    # les sommes SQL valent NULL quand aucun traitement n'est termine
    processing_sum, media_sum = processing_sum or 0, media_sum or 0
    return UsageStats(
        total=total,
        done=done,
        failed=failed,
        unfinished=unfinished,
        average_processing_seconds=processing_sum / done if done else None,
        realtime_factor=processing_sum / media_sum if media_sum else None,
    )


async def get_stats(session: AsyncSession) -> StatsResponse:
    """Statistiques d'usage, calculees par la base en une seule requete groupee par format."""
    query = select(
        Job.output_format,
        func.count(),
        _count_if(Job.status == JobStatus.DONE),
        _count_if(Job.status == JobStatus.FAILED),
        _count_if(Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING])),
        _done_sum(Job.processing_seconds),
        _done_sum(Job.media_seconds),
    ).group_by(Job.output_format)
    rows = (await session.execute(query)).all()

    by_format = {output_format: UsageStats() for output_format in OutputFormat}
    for output_format, *values in rows:
        by_format[output_format] = _to_stats(*values)

    # total general : somme colonne par colonne des lignes par format
    columns = zip(*(row[1:] for row in rows), strict=True) if rows else [()] * 6
    overall = _to_stats(*(sum(value or 0 for value in column) for column in columns))
    return StatsResponse(**overall.model_dump(), by_format=by_format)


async def list_jobs(
    session: AsyncSession,
    status: JobStatus | None,
    output_format: OutputFormat | None,
    user_id: int | None,
    limit,
    offset,
) -> list[Job]:
    query = select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
    if status:
        query = query.where(Job.status == status)
    if output_format:
        query = query.where(Job.output_format == output_format)
    if user_id:
        query = query.where(Job.user_id == user_id)
    return list(await session.scalars(query))


async def record_content_access(
    session: AsyncSession, job: Job, admin: UserAccount, request: ContentAccessRequest
) -> AdminContentAccess:
    access = AdminContentAccess(
        job_id=job.id, admin_id=admin.id, reason=request.reason, legal_reference=request.legal_reference
    )
    session.add(access)
    await session.commit()
    return access


async def list_content_accesses(session: AsyncSession, limit, offset) -> list[AdminContentAccess]:
    query = select(AdminContentAccess).order_by(AdminContentAccess.accessed_at.desc())
    return list(await session.scalars(query.limit(limit).offset(offset)))
