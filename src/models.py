"""Importe tous les modeles pour qu'ils soient connus de Base.metadata (Alembic, tests)."""

from src.admin.models import AdminContentAccess
from src.auth.models import UserAccount
from src.database import Base
from src.jobs.models import Job

__all__ = ["AdminContentAccess", "Base", "Job", "UserAccount"]
