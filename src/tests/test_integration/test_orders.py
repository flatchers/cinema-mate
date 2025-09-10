import pytest
from sqlalchemy import select, Result

from src.database.models import OrderModel
from src.database.models.order import StatusEnum
from src.database.models.accounts import UserGroupEnum, UserGroup, UserModel


@pytest.mark.asyncio
async def test_create_order_success_scenario(client, db_session):
    payload_register = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }

    db_session.add(UserGroup(name=UserGroupEnum.MODERATOR))
    await db_session.flush()

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR)
    result: Result = await db_session.execute(stmt)
    moderator_group = result.scalars().first()

    moderator = UserModel(
        email=payload_register["email"],
        password=payload_register["password"],
        group_id=moderator_group.id,
    )
    moderator.is_active = True
    db_session.add(moderator)
    await db_session.commit()
    assert moderator.is_active

    payload = {
        "username": payload_register["email"],
        "password": payload_register["password"],
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
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201
    response_data_movie = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
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
        "password": "StrongPassword123!",
    }

    db_session.add(UserGroup(name=UserGroupEnum.MODERATOR))
    await db_session.flush()

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR)
    result: Result = await db_session.execute(stmt)
    moderator_group = result.scalars().first()

    moderator = UserModel(
        email=payload_register["email"],
        password=payload_register["password"],
        group_id=moderator_group.id,
    )
    moderator.is_active = True
    db_session.add(moderator)
    await db_session.commit()
    assert moderator.is_active

    payload = {
        "username": payload_register["email"],
        "password": payload_register["password"],
    }

    response = await client.post("/api/v1/accounts/login/", data=payload)
    response_data_log = response.json()
    assert response.status_code == 200

    payload_movie = {
        "name": "Order",
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
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    # missing cart items creation

    response = await client.post(
        "/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 404
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


@pytest.mark.asyncio
async def test_create_order_409_existing_orders_conflict(client, db_session):
    payload_register = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }

    db_session.add(UserGroup(name=UserGroupEnum.MODERATOR))
    await db_session.flush()

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR)
    result: Result = await db_session.execute(stmt)
    moderator_group = result.scalars().first()

    moderator = UserModel(
        email=payload_register["email"],
        password=payload_register["password"],
        group_id=moderator_group.id,
    )
    moderator.is_active = True
    db_session.add(moderator)
    await db_session.commit()
    assert moderator.is_active

    payload = {
        "username": payload_register["email"],
        "password": payload_register["password"],
    }

    response = await client.post("/api/v1/accounts/login/", data=payload)
    response_data_log = response.json()
    assert response.status_code == 200

    payload_movie = {
        "name": "Order1",
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
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201
    response_data_movie = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
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

    payload_movie2 = {
        "name": "Order2",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "testing2",
        "price": 10.1,
        "certification": "testing2",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Middle Developer"],
    }

    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie2,
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201
    response_data_movie_2 = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie_2["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    payload_movie3 = {
        "name": "Order3",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "testing2",
        "price": 10.1,
        "certification": "testing2",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Middle Developer"],
    }

    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie3,
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201
    response_data_movie_3 = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie_3["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )

    assert response.status_code == 201

    response = await client.post(
        "/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 409
    response_data_order2 = response.json()
    existing_film = f"{payload_movie["name"]}"
    new_films = f"{payload_movie2["name"]}, {payload_movie3["name"]}"
    assert (
        response_data_order2["detail"]
        == f"{existing_film} already exist. {new_films} was added to order"
    )

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

    assert len(orders) == 2

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie_3["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )

    assert response.status_code == 201

    response = await client.post(
        "/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 409
    response_data_order2 = response.json()
    existing_film = f"{payload_movie["name"]}, {payload_movie3["name"]}"
    assert response_data_order2["detail"] == f"{existing_film} already exist."

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

    assert len(orders) == 2


@pytest.mark.asyncio
async def test_order_list(client, db_session):
    payload_register = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }

    db_session.add(UserGroup(name=UserGroupEnum.MODERATOR))
    await db_session.flush()

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR)
    result: Result = await db_session.execute(stmt)
    moderator_group = result.scalars().first()

    moderator = UserModel(
        email=payload_register["email"],
        password=payload_register["password"],
        group_id=moderator_group.id,
    )
    moderator.is_active = True
    db_session.add(moderator)
    await db_session.commit()
    assert moderator.is_active

    payload = {
        "username": payload_register["email"],
        "password": payload_register["password"],
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
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201
    response_data_movie = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
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

    response = await client.get(
        "/api/v1/orders/list/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data[0]["id"] == order.id
    assert response_data[0]["count_films"] == 1
    assert response_data[0]["status"] == order.status

    payload_movie2 = {
        "name": "Order2",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "testing2",
        "price": 10.1,
        "certification": "testing2",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Middle Developer"],
    }

    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie2,
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201
    response_data_movie_2 = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie_2["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    payload_movie3 = {
        "name": "Order3",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "testing2",
        "price": 10.1,
        "certification": "testing2",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["Middle Developer"],
    }

    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie3,
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201
    response_data_movie_3 = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie_3["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.get(
        "/api/v1/orders/list/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data[1]["id"] == order.id + 1
    assert response_data[1]["count_films"] == 2
    assert response_data[1]["status"] == StatusEnum.PENDING


@pytest.mark.asyncio
async def test_order_delete_success_scenario(client, db_session):
    payload_register = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }

    db_session.add(UserGroup(name=UserGroupEnum.MODERATOR))
    await db_session.flush()

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR)
    result: Result = await db_session.execute(stmt)
    moderator_group = result.scalars().first()

    moderator = UserModel(
        email=payload_register["email"],
        password=payload_register["password"],
        group_id=moderator_group.id,
    )
    moderator.is_active = True
    db_session.add(moderator)
    await db_session.commit()
    assert moderator.is_active

    payload = {
        "username": payload_register["email"],
        "password": payload_register["password"],
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
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201
    response_data_movie = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
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

    response = await client.delete(
        f"/api/v1/orders/delete/{order.id}/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 204

    await db_session.refresh(order)
    assert order.status == StatusEnum.CANCELED


@pytest.mark.asyncio
async def test_order_delete_invalid_scenarios(client, db_session):
    payload_register = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!",
    }

    db_session.add(UserGroup(name=UserGroupEnum.MODERATOR))
    await db_session.flush()

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR)
    result: Result = await db_session.execute(stmt)
    moderator_group = result.scalars().first()

    moderator = UserModel(
        email=payload_register["email"],
        password=payload_register["password"],
        group_id=moderator_group.id,
    )
    moderator.is_active = True
    db_session.add(moderator)
    await db_session.commit()
    assert moderator.is_active

    payload = {
        "username": payload_register["email"],
        "password": payload_register["password"],
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
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201
    response_data_movie = response.json()

    response = await client.post(
        f"/api/v1/shopping-carts/{response_data_movie["id"]}/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/v1/orders/add/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 201

    response = await client.delete(
        f"/api/v1/orders/delete/{9999}/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )

    assert response.status_code == 404
    response_data = response.json()
    assert response_data["detail"] == "Order not found."

    stmt = select(UserModel).where(UserModel.email == payload_register["email"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    stmt = select(OrderModel).where(OrderModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    order = result.scalars().first()
    assert order

    order.status = StatusEnum.CANCELED
    db_session.add(order)
    await db_session.commit()

    response = await client.delete(
        f"/api/v1/orders/delete/{order.id}/",
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"},
    )
    assert response.status_code == 403
    response_data = response.json()
    assert (
        response_data["detail"]
        == f"Cannot delete order with status: {order.status.value}"
    )
