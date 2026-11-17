from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from src.auth.models import UserAccount
from src.auth.service import get_user_by_api_key
from src.database import Session
from src.exceptions import NotAuthenticated, PermissionDenied

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def current_user(session: Session, api_key: Annotated[str | None, Security(api_key_header)]):
    user = await get_user_by_api_key(session, api_key) if api_key else None
    if user is None:
        raise NotAuthenticated()
    return user


CurrentUser = Annotated[UserAccount, Depends(current_user)]


async def current_admin(user: CurrentUser):
    if not user.is_admin:
        raise PermissionDenied()
    return user


CurrentAdmin = Annotated[UserAccount, Depends(current_admin)]
