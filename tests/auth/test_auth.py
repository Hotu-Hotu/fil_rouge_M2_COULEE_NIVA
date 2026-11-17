from conftest import auth
from src.auth.models import UserAccount
from src.auth.service import create_user, hash_api_key


async def test_missing_or_invalid_key_is_rejected(client):
    assert (await client.get("/jobs")).status_code == 401
    assert (await client.get("/jobs", headers=auth("wrong"))).status_code == 401


async def test_valid_key_is_accepted(client, user_key):
    assert (await client.get("/jobs", headers=auth(user_key))).status_code == 200


async def test_only_the_key_hash_is_stored(sessions):
    async with sessions() as session:
        user, api_key = await create_user(session, "Bob")
        stored = await session.get(UserAccount, user.id)
    assert stored.api_key_hash == hash_api_key(api_key)
    assert api_key not in stored.api_key_hash


async def test_admin_routes_need_an_admin(client, user_key, admin_key):
    assert (await client.get("/admin/stats", headers=auth(user_key))).status_code == 403
    assert (await client.get("/admin/stats", headers=auth(admin_key))).status_code == 200
