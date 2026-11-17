import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import UserAccount


def hash_api_key(api_key: str):
    return hashlib.sha256(api_key.encode()).hexdigest()


async def create_user(session: AsyncSession, name: str, is_admin=False) -> tuple[UserAccount, str]:
    """Cree un compte et renvoie sa cle d'API, affichee une seule fois."""
    api_key = secrets.token_urlsafe(32)
    user = UserAccount(name=name, api_key_hash=hash_api_key(api_key), is_admin=is_admin)
    session.add(user)
    await session.commit()
    return user, api_key


async def get_user_by_api_key(session: AsyncSession, api_key: str) -> UserAccount | None:
    query = select(UserAccount).where(UserAccount.api_key_hash == hash_api_key(api_key))
    return await session.scalar(query)
