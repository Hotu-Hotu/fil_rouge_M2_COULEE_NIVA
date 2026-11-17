from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.auth.models import UserAccount
from src.database import Base
from src.utils import utcnow


class AdminContentAccess(Base):
    """Trace de chaque consultation d'un contenu par un administrateur (exigence legale du PO)."""

    __tablename__ = "admin_content_access"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("job.id"), index=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    legal_reference: Mapped[str] = mapped_column(String(100))
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    admin: Mapped[UserAccount] = relationship(lazy="joined")
