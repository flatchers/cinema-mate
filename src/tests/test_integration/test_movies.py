import pytest
from sqlalchemy import select, Result

from database.models.accounts import UserGroup, UserGroupEnum, UserModel, RefreshTokenModel


@pytest.mark.asyncio
async def test_film_create(db_session, client):
    payload_register = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    db_session.add(UserGroup(name=UserGroupEnum.MODERATOR))
    await db_session.flush()

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR)
    result: Result = await db_session.execute(stmt)
    moderator_group = result.scalars().first()

    moderator = UserModel(
        email=payload_register["email"],
        password=payload_register["password"],
        group_id=moderator_group.id
    )
    moderator.is_active = True
    db_session.add(moderator)
    await db_session.commit()
    assert moderator.is_active

    payload = {
        "username": payload_register["email"],
        "password": payload_register["password"]
    }

    stmt = select(UserModel).where(UserModel.email == payload["username"])
    result: Result = await db_session.execute(stmt)
    moder = result.scalars().first()

    response = await client.post("/api/v1/accounts/login/", data=payload)
    assert response.status_code == 200
