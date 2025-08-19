import pytest
from sqlalchemy import select, Result

from src.database.models.accounts import UserGroup, UserGroupEnum, UserModel


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
    response_data = response.json()
    assert response.status_code == 200

    payload_movie = {
        "name": "Success Film Test",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "test for creating film",
        "price": 10.1,
        "certification": "test best",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Alaric Zaltzman"],
    }
    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie,
        headers={"Authorization": f"Bearer {response_data["access_token"]}"}
    )
    assert response.status_code == 201

    response_data = response.json()
    assert response_data["id"]
    assert response_data["name"] == "Success Film Test"
    assert response_data["year"] == 2020
    assert response_data["description"] == "test for creating film"
    assert response_data["certification"] == "test best"
    assert response_data["genres"] == ["drama"]
    assert response_data["directors"] == ["Jo Hoffman"]
    assert response_data["stars"] == ["Alaric Zaltzman"]


@pytest.mark.asyncio
async def test_film_create_invalid_scenarios(db_session, client):
    payload_register = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    db_session.add(UserGroup(name=UserGroupEnum.MODERATOR))
    db_session.add(UserGroup(name=UserGroupEnum.USER))
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

    response = await client.post("/api/v1/accounts/login/", data=payload)
    response_data = response.json()
    assert response.status_code == 200

    payload_movie = {
        "name": "Success Film Test",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "test for creating film",
        "price": 10.1,
        "certification": "test best",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Alaric Zaltzman"],
    }
    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie,
        headers={"Authorization": f"Bearer {response_data["access_token"]}"}
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie,
        headers={"Authorization": f"Bearer {response_data["access_token"]}"}
    )
    response_data = response.json()
    assert "error: (sqlite3.IntegrityError) UNIQUE constraint failed" in response_data["detail"]


@pytest.mark.asyncio
async def test_film_create_invalid_roles(client, db_session):
    payload_register = {
        "email": "sample@user.com",
        "password": "StrongPassword123!"
    }
    db_session.add(UserGroup(name=UserGroupEnum.USER))
    await db_session.flush()

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    result: Result = await db_session.execute(stmt)
    user_group = result.scalars().first()

    sample_user = UserModel(
        email=payload_register["email"],
        password=payload_register["password"],
        group_id=user_group.id
    )

    sample_user.is_active = True
    db_session.add(sample_user)
    await db_session.commit()
    assert sample_user.is_active

    payload = {
        "username": payload_register["email"],
        "password": payload_register["password"]
    }

    response = await client.post("/api/v1/accounts/login/", data=payload)
    response_data = response.json()
    assert response.status_code == 200

    payload_movie = {
        "name": "Success Film Test",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "test for creating film",
        "price": 10.1,
        "certification": "test best",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Alaric Zaltzman"],
    }

    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie,
        headers={"Authorization": f"Bearer {response_data["access_token"]}"}
    )
    assert response.status_code == 403, "Expected FOBIDDEN error"
    response_data = response.json()
    assert response_data["detail"] == "Access forbidden: insufficient permissions."
