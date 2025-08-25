import pytest
from sqlalchemy import select, Result
from sqlalchemy.orm import selectinload

from src.database.models import CartModel, CartItemsModel
from src.database.models.accounts import UserGroup, UserGroupEnum, UserModel


@pytest.mark.asyncio
async def test_add_cart_item(client, db_session):
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

    response = await client.post("/api/v1/accounts/login/", data=payload)
    response_data_log = response.json()
    assert response.status_code == 200

    payload_movie = {
        "name": "Rate Success",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "testing",
        "price": 10.1,
        "certification": "testing",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Junior Developer"],
    }
    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie,
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201
    response_data_movie = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201
    response_data = response.json()
    assert response_data_movie["id"] == response_data["create cart item"]["movie_id"]


@pytest.mark.asyncio
async def test_add_cart_item_invalid_scenarios(client, db_session):
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

    response = await client.post("/api/v1/accounts/login/", data=payload)
    response_data_log = response.json()
    assert response.status_code == 200

    payload_movie = {
        "name": "Rate Success",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "testing",
        "price": 10.1,
        "certification": "testing",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Junior Developer"],
    }
    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie,
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201
    response_data_movie = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201, "Expected message successful creation"

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 409, "Expected message: Movie already in cart"

    response = await client.post(
        f"/api/v1/shopping-carts/{9999}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 404, "Expected message: Movie not found"


@pytest.mark.asyncio
async def test_remove_cart_item(client, db_session):
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

    response = await client.post("/api/v1/accounts/login/", data=payload)
    response_data_log = response.json()
    assert response.status_code == 200

    payload_movie = {
        "name": "Rate Success",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "testing",
        "price": 10.1,
        "certification": "testing",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Junior Developer"],
    }
    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie,
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201
    response_data_movie = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201, "Expected message successful creation"
    response_data_cart = response.json()

    response = await client.delete(
        f"/api/v1/shopping-carts/{response_data_cart["create cart item"]["cart_id"]}/delete/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )

    assert response.status_code == 200
    response_data_remove = response.json()
    assert response_data_remove["message"] == "Movie deleted from cart successfully"

