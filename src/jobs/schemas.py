from datetime import datetime

from src.jobs.constants import JobStatus
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
    processing_seconds: float | None
    warnings: list[str]
    error: str | None
    files: list[JobFile]
