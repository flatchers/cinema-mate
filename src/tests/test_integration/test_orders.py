import pytest
from sqlalchemy import select, Result

from database.models import OrderModel
from src.database.models.accounts import UserGroupEnum, UserGroup, UserModel


@pytest.mark.asyncio
async def test_create_order_success_scenario(client, db_session):
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

    response = await client.post(
        f"/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201
    response_data_order = response.json()
    assert response_data_order["response"] == "Order created successfully"

    stmt = select(UserModel).where(UserModel.email == payload_register["email"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    stmt = select(OrderModel).where(OrderModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    order = result.scalars().first()
    assert order

    stmt = select(OrderModel).where(OrderModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    orders = result.scalars().all()

    assert len(orders) == 1


@pytest.mark.asyncio
async def test_create_order_409_empty_cart(client, db_session):
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

    # missing cart items creation

    response = await client.post(
        f"/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 409
    response_data = response.json()
    assert response_data["detail"] == "Your cart is empty"

    stmt = select(UserModel).where(UserModel.email == payload_register["email"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    stmt = select(OrderModel).where(OrderModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    order = result.scalars().first()
    assert not order

    stmt = select(OrderModel).where(OrderModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    orders = result.scalars().all()

    assert len(orders) == 0
