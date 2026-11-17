from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.auth.models import UserAccount
from src.database import Base, str_enum
from src.jobs.constants import JobStatus
from src.transcription.models import OutputFormat
from src.utils import utcnow


class Job(Base):
    __tablename__ = "job"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    output_format: Mapped[OutputFormat] = mapped_column(str_enum(OutputFormat))
    status: Mapped[JobStatus] = mapped_column(str_enum(JobStatus), default=JobStatus.QUEUED, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_name: Mapped[str | None] = mapped_column(String(100))

    # mesures, pour les statistiques et le suivi de la performance
    media_seconds: Mapped[float | None]
    processing_seconds: Mapped[float | None]

    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text)
    files: Mapped[list[str]] = mapped_column(JSON, default=list)
    transcript_text: Mapped[str | None] = mapped_column(Text)

    # purge : resultats supprimes apres la journee, puis tout le contenu apres 3 a 6 mois
    files_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserAccount] = relationship(lazy="joined")
