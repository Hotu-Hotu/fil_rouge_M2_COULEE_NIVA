from datetime import datetime

from pydantic import Field

from src.admin.models import AdminContentAccess
from src.auth.schemas import UserSummary
from src.jobs.constants import JobStatus
from src.jobs.models import Job
from src.schemas import CustomModel
from src.transcription.models import OutputFormat


class UsageStats(CustomModel):
    total: int = 0
    done: int = 0
    failed: int = 0
    # en attente ou en cours
    unfinished: int = 0
    average_processing_seconds: float | None = None
    # temps de calcul / duree du media : < 1 signifie plus rapide que le temps reel
    realtime_factor: float | None = None


class StatsResponse(UsageStats):
    by_format: dict[OutputFormat, UsageStats]


class AdminJobResponse(CustomModel):
    """Metadonnees d'un traitement, sans son contenu."""

    id: str
    user: UserSummary
    filename: str
    output_format: OutputFormat
    status: JobStatus
    created_at: datetime
    finished_at: datetime | None
    media_seconds: float | None
    processing_seconds: float | None
    error: str | None
    content_available: bool

    @classmethod
    def from_job(cls, job: Job):
        return cls(
            id=job.id,
            user=UserSummary(id=job.user.id, name=job.user.name),
            filename=job.filename,
            output_format=job.output_format,
            status=job.status,
            created_at=job.created_at,
            finished_at=job.finished_at,
            media_seconds=job.media_seconds,
            processing_seconds=job.processing_seconds,
            error=job.error,
            content_available=job.transcript_text is not None,
        )


class ContentAccessRequest(CustomModel):
    reason: str = Field(min_length=10, max_length=2000, description="Motif de la consultation")
    legal_reference: str = Field(
        min_length=3, max_length=100, description="Reference de l'autorisation legale (formulaire signe)"
    )


class ContentResponse(CustomModel):
    job_id: str
    transcript_text: str


class ContentAccessResponse(CustomModel):
    id: int
    job_id: str
    admin: UserSummary
    reason: str
    legal_reference: str
    accessed_at: datetime

    @classmethod
    def from_access(cls, access: AdminContentAccess):
        return cls(
            id=access.id,
            job_id=access.job_id,
            admin=UserSummary(id=access.admin.id, name=access.admin.name),
            reason=access.reason,
            legal_reference=access.legal_reference,
            accessed_at=access.accessed_at,
        )
