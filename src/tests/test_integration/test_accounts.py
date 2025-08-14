import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from sqlalchemy import Result, select
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.functions import count

from src.database.models import UserModel
from src.database.models.accounts import ActivationTokenModel, PasswordResetTokenModel
from src.main import app

transport = ASGITransport(app=app)


@pytest.mark.asyncio
async def test_user_registration(client, db_session):
    response = await client.post("/api/v1/accounts/register/", json={
        "email": "testuser@example.com",
        "password": "Ma@12345"
    }
                                 )
    assert response.status_code == 201

    data = response.json()
    stmt = select(UserModel).where(UserModel.email == data["email"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user.id == data["id"], "User not found"

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == UserModel.id)
    result: Result = await db_session.execute(stmt)
    activation_token = result.scalars().first()

    assert activation_token is not None, "Activation token is not created"
    assert activation_token.user_id == user.id
    assert activation_token.token is not None, "token is not created"
    assert activation_token.expires_at is not None, "Expired data is not create"


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_password, expected_error", [
    ("Sh0rt1", "Make sure your password is at lest 8 letters"),
    ("without1capitalletter", "Make sure your password has a capital letter in it"),
    ("WiThoutnumber", "Make sure your password has a number in it"),
])
async def test_user_registration_invalid_password(client, db_session, invalid_password, expected_error):
    response = await client.post("/api/v1/accounts/register/", json={
            "email": "testuser1@example.com",
            "password": invalid_password
    })

    assert response.status_code == 422

    response_data = response.json()
    assert expected_error in str(response_data), f"the error: {expected_error}"


@pytest.mark.asyncio
async def test_user_registration_conflict_scenarios(client, db_session):

    payload = {
        "email": "conflictuser@example.com",
        "password": "Ma@12345"
    }

    response = await client.post("/api/v1/accounts/register/", json=payload)
    assert response.status_code == 201, "should be first user registration"

    response_data = response.json()

    stmt = select(UserModel).where(UserModel.email == response_data["email"])
    result: Result = await db_session.execute(stmt)
    created_user = result.scalars().first()

    assert created_user is not None, "Created first user"
    response = await client.post("/api/v1/accounts/register/", json=payload)
    assert response.status_code == 409, "should be conflict"

    response_data = response.json()
    expected_message = "Email already exist"
    assert response_data["detail"] == expected_message, f"should be error {expected_message}"


@pytest.mark.asyncio
async def test_user_token_activation_success(client, db_session):
    payload = {
        "email": f"testuser@example.com",
        "password": "Ma@12345"
    }

    response = await client.post("/api/v1/accounts/register/", json=payload)
    response_data = response.json()
    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .where(ActivationTokenModel.user_id == response_data["id"])
    )
    result: Result = await db_session.execute(stmt)
    token = result.scalars().first()

    assert token.user.is_active is False, "after registration, user is not active"

    token_payload = {
        "email": f"testuser@example.com",
        "token": token.token
    }
    response_token = await client.post("/api/v1/accounts/activate/", json=token_payload)
    assert response_token.status_code == 200
    stmt = (
        select(UserModel)
        .options(joinedload(UserModel.activation_token))
        .where(UserModel.email == response_data["email"])
    )
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()
    response_data_2 = response_token.json()
    expected_message = "Activation successful"
    await db_session.refresh(user)
    assert response_data_2["detail"] == expected_message, f"Expected message - {expected_message}"
    assert user.is_active is True, "Expected activated user account"
    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .where(ActivationTokenModel.user_id == user.id)
    )
    result: Result = await db_session.execute(stmt)
    new_token = result.scalars().first()
    assert new_token is None, "Expected delete token after activation"


@pytest.mark.asyncio
async def test_user_token_activation_invalid_scenarios(client, db_session):
    payload = {
        "email": f"testuser@example.com",
        "password": "Ma@12345"
    }

    response = await client.post("/api/v1/accounts/register/", json=payload)
    assert response.status_code == 201

    response_data = response.json()

    payload_token = {
        "email": "testuser@example.com",
        "token": str(uuid4())
    }

    response_token = await client.post("/api/v1/accounts/activate/", json=payload_token)

    response_data_token = response_token.json()
    expected_message = "Invalid token entered"
    assert response_data_token["detail"] == expected_message, f"Expected message - {expected_message}"

    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .where(ActivationTokenModel.user_id == response_data["id"])
    )
    result: Result = await db_session.execute(stmt)
    token = result.scalars().first()

    assert payload_token["token"] != token.token

    payload_token_true = {
        "email": "testuser@example.com",
        "token": token.token
    }

    response_2 = await client.post("/api/v1/accounts/activate/", json=payload_token_true)
    assert response_2.status_code == 200, "Expected token is activated"
    response_data_2 = response_2.json()
    assert response_data_2["detail"] == "Activation successful", "Expected activation successful"

    stmt = select(UserModel).where(UserModel.email == payload_token_true["email"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    assert not user.is_active
    await db_session.refresh(user)
    assert user.is_active

    stmt = (
        select(UserModel)
        .options(joinedload(UserModel.activation_token))
        .where(UserModel.id == user.id)
    )
    result = await db_session.execute(stmt)
    user_last = result.scalars().first()
    await db_session.refresh(user_last)

    response_3 = await client.post("/api/v1/accounts/activate/", json=payload_token_true)
    assert response_3.status_code == 409, "user should be already active"
    response_data_3 = response_3.json()

    assert response_data_3["detail"] == "You are already active"


@pytest.mark.asyncio
async def test_user_password_reset(client, db_session):
    payload = {
        "email": f"testuser@example.com",
        "password": "Ma@12345"
    }
    response_register = await client.post("/api/v1/accounts/register/", json=payload)
    assert response_register.status_code == 201

    stmt = (
        select(ActivationTokenModel)
        .join(UserModel)
        .where(UserModel.email == payload["email"])
    )
    result: Result = await db_session.execute(stmt)
    token = result.scalars().first()

    payload = {
        "email": "testuser@example.com",
        "token": token.token
    }

    response = await client.post("/api/v1/accounts/activate/", json=payload)

    assert response.status_code == 200

    stmt = (
        select(UserModel)
        .options(joinedload(UserModel.password_reset_token))
        .where(UserModel.email == payload["email"])
    )
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    payload = {
        "email": "testuser@example.com"
    }
    response = await client.post("/api/v1/accounts/password-reset/request/", json=payload)

    stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    reset_password = result.scalars().all()

    assert user.password_reset_token is None
    await db_session.refresh(user)
    assert user.password_reset_token is not None
    assert len(reset_password) == 1
    response_data = response.json()
    assert response_data["message"] == "Request successful"
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_user_password_reset_invalid_scenarios(client, db_session):
    payload = {
        "email": f"testuser@example.com",
        "password": "Ma@12345"
    }
    response_register = await client.post("/api/v1/accounts/register/", json=payload)
    assert response_register.status_code == 201
    response_data2 = response_register.json()

    stmt = (
        select(ActivationTokenModel)
        .join(UserModel)
        .where(UserModel.email == payload["email"])
    )
    result: Result = await db_session.execute(stmt)
    token = result.scalars().first()

    payload = {
        "email": "testuser@example.com",
        "token": token.token
    }

    response = await client.post("/api/v1/accounts/activate/", json=payload)

    assert response.status_code == 200

    invalid_email = {
        "email": "notcurrentemail@example.com"
    }
    response = await client.post("/api/v1/accounts/password-reset/request/", json=invalid_email)

    stmt = select(UserModel).options(joinedload(UserModel.password_reset_token)).where(UserModel.id == response_data2["id"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user.password_reset_token is None

    assert response.status_code == 400

    response_data = response.json()
    assert response_data["detail"] == "Invalid email or password", \
        "Expected -- 'Invalid email or password'"

    payload = {
        "email": "testuser@example.com"
    }

    response = await client.post("/api/v1/accounts/password-reset/request/", json=payload)
    assert response.status_code == 200

    stmt = select(UserModel).options(joinedload(UserModel.password_reset_token)).where(UserModel.id == response_data2["id"])
    result: Result = await db_session.execute(stmt)
    user = result.scalars().first()

    stmt = select(PasswordResetTokenModel).join(UserModel).where(PasswordResetTokenModel.user_id == user.id)
    result: Result = await db_session.execute(stmt)
    password_reset = result.scalars().all()

    assert len(password_reset) == 1
    response = await client.post("/api/v1/accounts/password-reset/request/", json=payload)

    assert response.status_code == 200

    assert user.password_reset_token is None
    await db_session.refresh(user)
    assert user.password_reset_token is not None
    assert len(password_reset) == 1

