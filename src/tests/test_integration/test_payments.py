from unittest.mock import patch

import pytest
import stripe
from sqlalchemy import select, Result
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.database.models import OrderModel, OrderItemModel
from src.database.models.order import StatusEnum
from src.database.models.accounts import UserGroup, UserGroupEnum, UserModel

stripe.api_key = settings.STRIPE_SECRET_KEY


@patch("src.routes.payments.stripe.checkout.Session.create")
@pytest.mark.asyncio
async def test_payment_add_success_scenario(mock_payment_add, client, db_session):
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
        "name": "Order Success",
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

    stmt = select(UserModel).where(UserModel.email == payload_register["email"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    stmt = (
        select(OrderModel)
        .options(selectinload(OrderModel.order_items).selectinload(OrderItemModel.movie))
        .where(OrderModel.user_id == user.id)
    )
    result: Result = await db_session.execute(stmt)
    order = result.scalars().first()
    assert order

    mock_payment_add.return_value = {
        "id": "cs_test_123",
        "url": "https://fake-checkout.stripe.com/test"
    }

    response = await client.post(
        f"/api/v1/payments/add/{order.id}/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["response"] == "payment add successfully"


@patch("src.routes.payments.stripe.checkout.Session.create")
@pytest.mark.asyncio
async def test_payment_add_409_scenarios(mock_payment_add, client, db_session):
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
        "name": "Order Success",
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

    stmt = select(UserModel).where(UserModel.email == payload_register["email"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    stmt = (
        select(OrderModel)
        .options(selectinload(OrderModel.order_items).selectinload(OrderItemModel.movie))
        .where(OrderModel.user_id == user.id)
    )
    result: Result = await db_session.execute(stmt)
    order = result.scalars().first()
    assert order

    mock_payment_add.return_value = {
        "id": "cs_test_123",
        "url": "https://fake-checkout.stripe.com/test"
    }

    response = await client.post(
        f"/api/v1/payments/add/{order.id}/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201

    response = await client.post(
        f"/api/v1/payments/add/{order.id}/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 409
    response_data = response.json()
    assert response_data["detail"] == "payment already exist"


@patch("src.routes.payments.stripe.checkout.Session.create")
@pytest.mark.asyncio
async def test_payment_add_404_scenario(mock_payment_add, client, db_session):
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
        "name": "Order Success",
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

    stmt = select(UserModel).where(UserModel.email == payload_register["email"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    stmt = (
        select(OrderModel)
        .options(selectinload(OrderModel.order_items).selectinload(OrderItemModel.movie))
        .where(OrderModel.user_id == user.id)
    )
    result: Result = await db_session.execute(stmt)
    order = result.scalars().first()
    order.status = StatusEnum.PAID
    await db_session.commit()
    assert order

    mock_payment_add.return_value = {
        "id": "cs_test_123",
        "url": "https://fake-checkout.stripe.com/test"
    }

    response = await client.post(
        f"/api/v1/payments/add/{order.id}/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 404
    response_data = response.json()
    assert response_data["detail"] == "Order not found"

    order.status = StatusEnum.PENDING
    await db_session.commit()
    assert order.status == StatusEnum.PENDING.value

    response = await client.post(
        f"/api/v1/payments/add/{9999}/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 404
    response_data = response.json()
    assert response_data["detail"] == "Order not found"


@patch("src.routes.payments.stripe.checkout.Session.create")
@pytest.mark.asyncio
async def test_webhook_success(mock_payment_add, client, db_session):
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
        "name": "Order Success",
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

    stmt = select(UserModel).where(UserModel.email == payload_register["email"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    stmt = (
        select(OrderModel)
        .options(selectinload(OrderModel.order_items).selectinload(OrderItemModel.movie))
        .where(OrderModel.user_id == user.id)
    )
    result: Result = await db_session.execute(stmt)
    order = result.scalars().first()
    assert order

    mock_payment_add.return_value = {
        "id": "cs_test_123",
        "url": "https://fake-checkout.stripe.com/test"
    }

    response = await client.post(
        f"/api/v1/payments/add/{order.id}/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201

    fake_event = {
        "id": "evt_test_123",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "pi_test_123",
                "object": "payment_intent"
            }
        }
    }

    response = await client.post(
        f"/api/v1/payments/webhook/",
        json=fake_event,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["response"] == "Successful"
