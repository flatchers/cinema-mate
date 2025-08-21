import pytest
from sqlalchemy import select, Result

from src.database.models.shopping_cart import CartModel, CartItemsModel
from src.database.models import Movie, PaymentModel, OrderItemModel, OrderModel, UserModel
from src.database.models.order import StatusEnum
from src.database.models.accounts import UserGroup, UserGroupEnum


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

    stmt = select(Movie).where(Movie.id == response_data["id"])
    result: Result = await db_session.execute(stmt)
    movie = result.scalars().first()

    stmt = select(Movie).where(Movie.id == response_data["id"])
    result: Result = await db_session.execute(stmt)
    movies = result.scalars().all()

    assert movie
    assert movies
    assert movie.id == response_data["id"]
    assert len(movies) == 1

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


@pytest.mark.asyncio
async def test_movie_update_success(client, db_session):
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
    response_data = response.json()
    assert response_data["access_token"]
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
    response_name = response.json()
    assert response_name["name"] == "Success Film Test"

    payload_movie["name"] = "Success Updated"
    response = await client.patch(
        f"/api/v1/movies/update/{response_name["id"]}/",
        json=payload_movie,
        headers={"Authorization": f"Bearer {response_data["access_token"]}"}
    )
    assert response.status_code == 200

    response_data = response.json()
    assert response_data["new movie"]["name"] == "Success Updated"


@pytest.mark.asyncio
async def test_movie_delete(client, db_session):
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
    response_data_token = response.json()
    assert response_data_token["access_token"]
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
        headers={"Authorization": f"Bearer {response_data_token["access_token"]}"}
    )
    response_data_create = response.json()
    assert response.status_code == 201

    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movie = result.scalars().first()

    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movies = result.scalars().all()

    assert movie
    assert movies
    assert movie.id == response_data_create["id"]
    assert len(movies) == 1

    response = await client.delete(
        f"/api/v1/movies/delete/{response_data_create["id"]}/",
        headers={"Authorization": f"Bearer {response_data_token["access_token"]}"}
        )
    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movie = result.scalars().first()

    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movies = result.scalars().all()

    assert not movie
    assert not movies
    assert len(movies) == 0

    assert response.status_code == 200
    response_data_delete = response.json()
    assert response_data_delete["detail"] == "Movie deleted successfully"


@pytest.mark.asyncio
async def test_delete_nonexistent_movie_returns_404(client, db_session):
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
    response_data_token = response.json()
    assert response_data_token["access_token"]
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
        headers={"Authorization": f"Bearer {response_data_token["access_token"]}"}
    )
    response_data_create = response.json()
    assert response.status_code == 201

    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movie = result.scalars().first()

    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movies = result.scalars().all()

    assert movie
    assert movies
    assert movie.id == response_data_create["id"]
    assert len(movies) == 1

    response = await client.delete(
        f"/api/v1/movies/delete/{response_data_create["id"]}/",
        headers={"Authorization": f"Bearer {response_data_token["access_token"]}"}
    )
    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movie = result.scalars().first()

    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movies = result.scalars().all()

    assert not movie
    assert not movies
    assert len(movies) == 0

    assert response.status_code == 200
    response_data_delete = response.json()
    assert response_data_delete["detail"] == "Movie deleted successfully"

    response = await client.delete(
        f"/api/v1/movies/delete/{response_data_create["id"]}/",
        headers={"Authorization": f"Bearer {response_data_token["access_token"]}"}
        )
    assert response.status_code == 404
    response_data = response.json()
    assert response_data["detail"] == "movie not found"


@pytest.mark.asyncio
async def test_purchase_conflict_when_film_already_bought(client, db_session):
    payload_register = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    db_session.add(UserGroup(name=UserGroupEnum.MODERATOR))
    await db_session.flush()

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR)
    result: Result = await db_session.execute(stmt)
    user_group = result.scalars().first()

    assert user_group is not None

    user = UserModel(
        email=payload_register["email"],
        password=payload_register["password"],
        group_id=user_group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()
    assert user.is_active

    payload = {
        "username": payload_register["email"],
        "password": payload_register["password"]
    }

    response = await client.post("/api/v1/accounts/login/", data=payload)
    response_data_token = response.json()
    assert response_data_token["access_token"]
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
        headers={"Authorization": f"Bearer {response_data_token["access_token"]}"}
    )
    assert response.status_code == 201
    response_data_create = response.json()
    print(response_data_create)

    stmt = select(UserModel).where(UserModel.email == payload["username"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movie = result.scalars().first()
    print("MOVIE ID", movie.id)

    cart_create = CartModel(
        user_id=user.id,
    )
    db_session.add(cart_create)
    await db_session.commit()
    stmt = select(CartModel).where(CartModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    cart = result.scalars().first()
    assert cart
    print("CART ID: ", cart.id)

    cart_items_create = CartItemsModel(
        cart_id=cart.id,
        movie_id=movie.id,
    )
    db_session.add(cart_items_create)
    await db_session.commit()

    order_create = OrderModel(
        user_id=user.id,
        status=StatusEnum.PAID,
        total_amount=movie.price
    )
    db_session.add(order_create)
    await db_session.commit()

    stmt = select(OrderModel).where(OrderModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    order = result.scalars().first()
    assert order

    order_items = OrderItemModel(
        order_id=order.id,
        movie_id=movie.id,
        price_at_order=movie.price
    )
    db_session.add(order_items)
    await db_session.commit()
    assert order_items
    assert order.status == StatusEnum.PAID

    stmt = select(OrderItemModel).join(OrderModel).where(OrderModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    order_item = result.scalars().first()

    assert order_item
    print("ORDER_ITEM ID", order_item.id)

    payment_create = PaymentModel(
        user_id=user.id,
        order_id=order.id,
        amount=order.total_amount
    )
    db_session.add(payment_create)
    await db_session.commit()

    stmt = select(PaymentModel).where(PaymentModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    payment = result.scalars().first()

    assert payment

    response = await client.delete(
        f"/api/v1/movies/delete/{response_data_create["id"]}/",
        headers={"Authorization": f"Bearer {response_data_token["access_token"]}"}
        )
    assert response.status_code == 409, "Expected message: current film is bought"

    stmt = select(Movie).where(Movie.id == response_data_create["id"])
    result: Result = await db_session.execute(stmt)
    movie = result.scalars().all()

    assert len(movie) == 1


@pytest.mark.asyncio
async def test_movie_list_success(client, db_session):

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

    response = await client.get("/api/v1/movies/lists/")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["movies"]) == 1
    assert response_data["prev_page"] is None
    assert response_data["next_page"] is None
    assert response_data["total_pages"] == 1
    assert response_data["total_items"] == 1


@pytest.mark.asyncio
async def test_movie_list_invalid_scenarios(client, db_session):

    response = await client.get("/api/v1/movies/lists/")
    assert response.status_code == 404
    response_data = response.json()
    assert response_data["detail"] == "No movies found."


@pytest.mark.asyncio
async def test_movie_search_success(client, db_session):
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
        "name": "aaa",
        "year": 2020,
        "time": 130,
        "imdb": 6.1,
        "votes": 100,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "aaa",
        "price": 10.1,
        "certification": "aaaaaaaaa",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["aaa"],
    }
    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_movie,
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201

    response = await client.post("/api/v1/movies/search/", params={"search": "aaa"})
    assert response.status_code == 200
    response_data = response.json()
    assert response_data[0]["name"] == "aaa"
    assert len(response_data) == 1

    payload_new = {
        "name": "att",
        "year": 2021,
        "time": 131,
        "imdb": 6.1,
        "votes": 101,
        "meta_score": 10.1,
        "gross": 9.1,
        "description": "ttt ",
        "price": 10.0,
        "certification": "ttt",
        "genres": ["drama"],
        "directors": ["Jo Hoffman"],
        "stars": ["ttt"],
    }
    response = await client.post(
        "/api/v1/movies/create/",
        json=payload_new,
        headers={"Authorization": f"Bearer {response_data_log["access_token"]}"}
    )
    assert response.status_code == 201

    response = await client.post("/api/v1/movies/search/", params={"search": "tt"})
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1

    response = await client.post("/api/v1/movies/search/", params={"search": "a"})
    assert response.status_code == 200
    response_data_two = response.json()
    assert len(response_data_two) == 2


@pytest.mark.asyncio
async def test_movie_search_empty_list(client, db_session):
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
    assert response.status_code == 200

    response = await client.post("/api/v1/movies/search/", params={"search": "tt"})
    assert response.status_code == 200
    response_data = response.json()
    assert not response_data


@pytest.mark.asyncio
async def test_movie_detail(client, db_session):
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
    print(response_data)

    response = await client.get("/api/v1/movies/detail/", params={"movie_id": response_data["id"]})
    assert response.status_code == 200

    response_data_detail = response.json()
    print("DETAIL", response_data_detail)
    assert response_data_detail["name"] == response_data["name"]




