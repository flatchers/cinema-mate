from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.accounts import (
    UserModel,
    UserGroup,
    UserGroupEnum,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
)
from src.database import get_db
from src.notifications.send_email.send_activation_email import send_activation_email
from src.notifications.send_email.send_activation_email_complete import (
    send_activation_email_confirm,
)
from src.notifications.send_email.send_password_confirm_email import (
    send_password_confirm,
)
from src.notifications.send_email.send_password_reset_email import (
    send_password_reset_email,
)
from src.schemas.accounts import (
    UserCreateResponse,
    UserCreateRequest,
    TokenActivationRequest,
    TokenResetPasswordRequest,
    UserLoginResponse,
    TokenResetPasswordCompleteRequest,
    MessageResponse,
    AccessTokenResponse,
    RefreshTokenRequest,
    AdminUpdateRequest,
)
from src.security.token_manipulation import (
    create_refresh_token,
    create_access_token,
    get_current_user,
    authenticate_user,
    get_user_token,
    decode_token,
)
from src.security.validations import password_validator_func, password_hash_pwd

router = APIRouter()


@router.post(
    "/register/",
    response_model=UserCreateResponse,
    summary="User Registration",
    description="Register user with email and password",
    status_code=status.HTTP_201_CREATED,
)
async def user_registration(
    schema: UserCreateRequest, session: AsyncSession = Depends(get_db)
):
    """
    User Registration

     This endpoint allows registration for
     users with hashing password and email.
     Arguments:
     1) schema - this is input data from pydentic model for registration
     2) session - query to database

     Returns:


     return UserCreateResponse model
    """

    stmt_email = select(UserModel).where(UserModel.email == schema.email)
    result_email = await session.execute(stmt_email)
    user_email = result_email.scalars().first()

    stmt_group = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    result_group = await session.execute(stmt_group)
    user_group = result_group.scalars().first()

    if user_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already exist"
        )

    if not user_group:
        user_group = UserGroup(name=UserGroupEnum.USER)
        session.add(user_group)
        await session.commit()

    try:
        new_user = UserModel(
            email=schema.email,
            password=password_validator_func(schema.password),
            group_id=user_group.id,
        )
        session.add(new_user)
        await session.flush()

        activate_token = ActivationTokenModel(user_id=new_user.id)
        session.add(activate_token)
        await session.commit()
        await session.refresh(new_user)
        print(activate_token.token)

    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during user creation. -- {e}",
        ) from e
    send_activation_email(schema.email, activate_token.token)
    return UserCreateResponse(
        id=new_user.id,
        email=new_user.email,
    )


@router.post(
    "/activate/",
    summary="Activation Token",
    description="Activate token with token argument",
    status_code=status.HTTP_200_OK,
)
async def user_token_activation(
    schema: TokenActivationRequest, session: AsyncSession = Depends(get_db)
):
    """
    Activation Token

    The endpoint allows to activate user account
    with provided data. User gets secure token.
    After activation token, user can log in, logout from account,
    schema: input data from pydentic model for activation token
    session: query to database
    return: message
    """

    stmt_token = (
        select(ActivationTokenModel)
        .join(UserModel)
        .where(
            ActivationTokenModel.token == schema.token, UserModel.email == schema.email
        )
    )
    result_token = await session.execute(stmt_token)
    activ_token = result_token.scalars().first()

    stmt_user = select(UserModel).where(UserModel.email == schema.email)
    result_user = await session.execute(stmt_user)
    user = result_user.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{schema.email} does not exist",
        )
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You are already active"
        )
    if not activ_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid token entered"
        )
    if schema.token != activ_token.token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid token entered"
        )

    user.is_active = True
    await session.delete(activ_token)
    await session.commit()

    send_activation_email_confirm(schema.email, schema.token)

    return {"detail": "Activation successful"}


@router.post(
    "/password-reset/request/",
    summary="Password Reset Request",
    description="reset password request with email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def user_password_reset(
    schema: TokenResetPasswordRequest, session: AsyncSession = Depends(get_db)
):
    """
    Password Reset Request
    The endpoint allow reset password by entering email if tokens are equals
    schema: input data from pydentic model for reset password
    session: query to database
    return: MessageResponse
    """
    user_stmt = select(UserModel).where(UserModel.email == schema.email)
    user_result = await session.execute(user_stmt)
    db_user = user_result.scalars().first()

    if not db_user or not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password"
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is not active"
        )
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email"
        )

    await session.execute(
        delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == db_user.id
        )
    )
    try:
        new_token = PasswordResetTokenModel(user_id=db_user.id)
        session.add(new_token)
        await session.commit()

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e)
    print(new_token.token)

    send_password_reset_email(schema.email, new_token.token)

    return {"message": "Request successful"}


@router.post(
    "/password-reset/complete/",
    summary="Password Reset Confirm",
    description="refresh password",
    status_code=status.HTTP_200_OK,
)
async def reset_password_confirm(
    schema: TokenResetPasswordCompleteRequest, session: AsyncSession = Depends(get_db)
):
    """
    Password Reset Confirm

    The endpoint allow you

    schema: input data from pydentic model for setting a new password
    session: query to database
    return: Message
    """
    stmt_user = select(UserModel).where(UserModel.email == schema.email)
    result_user = await session.execute(stmt_user)
    db_user = result_user.scalars().first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    stmt_reset_token = select(PasswordResetTokenModel).where(
        PasswordResetTokenModel.user_id == db_user.id
    )
    result_token = await session.execute(stmt_reset_token)
    reset_token = result_token.scalars().first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    if reset_token.token != schema.token:
        delete_query = delete(RefreshTokenModel).where(
            RefreshTokenModel.user_id == db_user.id
        )
        await session.execute(delete_query)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    current_time = datetime.now(timezone.utc)
    if reset_token.expires_at.replace(tzinfo=timezone.utc) < current_time:
        delete_query = delete(RefreshTokenModel).where(
            RefreshTokenModel.user_id == db_user.id
        )
        await session.execute(delete_query)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token time expired"
        )

    try:
        db_user._hashed_password = password_hash_pwd(
            password_validator_func(schema.password)
        )
        delete_query = delete(RefreshTokenModel).where(
            RefreshTokenModel.user_id == db_user.id
        )
        await session.execute(delete_query)
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during user creation. -- {e}",
        )
    send_password_confirm(schema.email, reset_token.token)

    return {"message": "password successfully changed"}


@router.post(
    "/login/",
    summary="Login Account",
    description="log in account using buttons",
    response_model=UserLoginResponse,
)
async def user_login(
    session: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Login Account

    Allow user to sign in with the provided credentials
    session: query to database
    form_data: provided button for entering to account
    return: UserLoginResponse
    """
    email = form_data.username
    password = form_data.password

    stmt_user = (
        select(UserModel)
        .options(selectinload(UserModel.group))
        .where(UserModel.email == email)
    )
    result_user = await session.execute(stmt_user)
    db_user = result_user.scalars().first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    if not db_user.verify_password_pwd(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    refresh = create_refresh_token({"sub": str(db_user.id)})
    try:
        refresh_token = RefreshTokenModel(user_id=db_user.id, token=refresh)

        session.add(refresh_token)
        await session.commit()

    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during user creation. -- {e}",
        )

    access = create_access_token({"sub": str(db_user.id), "role": db_user.group.name})
    return {
        "access_token": access,
        "role": db_user.group.name,
        "refresh_token": refresh_token.token,
    }


@router.post(
    "/logout/",
    summary="Logout",
    description="log out of your account",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    token: str = Depends(get_user_token),
    session: AsyncSession = Depends(get_db),
):
    """
    Logout

    Allows logout of account
    current_user: current user's argument
    token: current token
    session: query to database
    return: MessageResponse
    """
    current_time = datetime.now(timezone.utc)

    stmt = select(RefreshTokenModel).where(RefreshTokenModel.user_id == current_user.id)
    refresh_result = await session.execute(stmt)
    refresh = refresh_result.scalars().first()

    if not refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated"
        )

    if refresh.expires_at.replace(tzinfo=timezone.utc) < current_time:
        await session.delete(refresh)
        await session.commit()
        return {"token": token, "message": "Session expired and token removed"}

    await session.delete(refresh)
    await session.commit()

    return {"message": "Logged out successfully"}


@router.post(
    "/refresh/",
    summary="Getting new access token",
    description="Getting new access token provided current refresh token",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh token

    Getting new access token provided current refresh token

    token_data: schema for input
    db: query to database
    return: AccessTokenResponse
    """
    try:
        decoded_token = decode_token(token_data.refresh_token)
        user_id = decoded_token.get("sub")
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    stmt_refresh = select(RefreshTokenModel).filter_by(token=token_data.refresh_token)
    result = await db.execute(stmt_refresh)
    refresh_token_record = result.scalars().first()
    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    stmt = select(UserModel).filter_by(id=user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    new_access_token = create_access_token(
        {
            "sub": str(user_id),
        }
    )

    return AccessTokenResponse(access_token=new_access_token)


@router.post(
    "/update/{user_id}/",
    response_model=MessageResponse,
    summary="User update",
    description="Update specific user by its ID",
    status_code=status.HTTP_200_OK,
)
async def update_user(
    user_id: int,
    schema: AdminUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    User Update

    allows administrators changing role & activation account

    user_id: indicates the user id that will be changed
    schema: schema for input for updating
    session: query to database
    current_user: current user
    return: message
    """

    stmt = (
        select(UserModel)
        .options(selectinload(UserModel.group))
        .where(UserModel.id == user_id)
    )
    result = await session.execute(stmt)
    user = result.scalars().first()

    stmt = (
        select(UserModel)
        .options(selectinload(UserModel.group))
        .where(UserModel.id == current_user.id)
    )
    result = await session.execute(stmt)
    now_user = result.scalars().first()

    stmt_group = select(UserGroup).where(UserGroup.name == schema.group)
    result_group = await session.execute(stmt_group)
    user_group = result_group.scalars().first()

    if not now_user or not now_user.group:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This function is only for admins",
        )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if now_user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="this function for admins"
        )

    if user.group.name == schema.group:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"you try change role {user.group.name} -> {schema.group}",
        )

    if not user_group:
        user_group = UserGroup(name=schema.group)
        session.add(user_group)
        await session.flush()
        user.group_id = user_group.id
        await session.commit()
        await session.refresh(user)

    user.group_id = user_group.id
    user.is_active = schema.is_active
    await session.commit()

    return {
        "message": f"Successful updated user_id "
        f"{user.id}: {user.group.name}, {user.group_id} -> "
        f"{schema.group}",
    }
