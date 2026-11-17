from datetime import datetime

from src.jobs.constants import JobStatus
from src.jobs.models import Job
from src.schemas import CustomModel
from src.transcription.models import OutputFormat


class JobFile(CustomModel):
    name: str
    url: str


class JobResponse(CustomModel):
    id: str
    filename: str
    output_format: OutputFormat
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    media_seconds: float | None
    processing_seconds: float | None
    warnings: list[str]
    error: str | None
    files: list[JobFile]
    # vrai une fois la journee passee : les resultats ne sont plus telechargeables
    files_expired: bool

    @classmethod
    def from_job(cls, job: Job):
        return cls(
            id=job.id,
            filename=job.filename,
            output_format=job.output_format,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            media_seconds=job.media_seconds,
            processing_seconds=job.processing_seconds,
            warnings=job.warnings,
            error=job.error,
            files=[JobFile(name=name, url=f"/jobs/{job.id}/files/{name}") for name in job.files],
            files_expired=job.files_deleted_at is not None,
        )
