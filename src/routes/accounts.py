from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.accounts import UserModel, UserGroup, UserGroupEnum, ActivationTokenModel, \
    PasswordResetTokenModel, RefreshTokenModel
from src.database.session_sqlite import get_db
from src.schemas.accounts import UserCreateResponse, UserCreateRequest, TokenActivationRequest, \
    TokenResetPasswordRequest, UserLoginRequest, UserLoginResponse, TokenResetPasswordCompleteRequest, MessageResponse, \
    AccessTokenResponse, RefreshTokenRequest
from src.security.token_manipulation import create_refresh_token, create_access_token, get_current_user, \
    authenticate_user, get_user_token, decode_token
from src.security.validations import verify_password, password_validator_func, password_hash_pwd

router = APIRouter()


@router.get("/list/")
async def list_users(db: AsyncSession = Depends(get_db)):
    stmt = select(UserModel)
    stmt_res = await db.execute(stmt)
    return stmt_res.scalars().all()


@router.post("/register/", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def user_registration(schema: UserCreateRequest, session: AsyncSession = Depends(get_db)):

    stmt_email = select(UserModel).where(UserModel.email == schema.email)
    result_email = await session.execute(stmt_email)
    user_email = result_email.scalars().first()

    stmt_group = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    result_group = await session.execute(stmt_group)
    user_group = result_group.scalars().first()

    if user_email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email already exist"
        )

    if not user_group:
        user_group = UserGroup(
            name=UserGroupEnum.USER
        )
        session.add(user_group)
        await session.commit()

    try:
        new_user = UserModel(
            email=schema.email,
            password=schema.password,
            group_id=user_group.id
        )
        session.add(new_user)
        await session.flush()

        activate_token = ActivationTokenModel(user_id=new_user.id)
        session.add(activate_token)
        await session.commit()
        print(activate_token.token)
        print("USER", new_user)

    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during user creation. -- {e}"
        ) from e

    return new_user


@router.post("/activate/", status_code=status.HTTP_200_OK)
async def user_token_activation(schema: TokenActivationRequest, session: AsyncSession = Depends(get_db)):

    stmt_token = select(ActivationTokenModel).where(ActivationTokenModel.token == schema.token)
    result_token = await session.execute(stmt_token)
    activ_token = result_token.scalars().first()

    stmt_user = select(UserModel).where(UserModel.email == schema.email)
    result_user = await session.execute(stmt_user)
    user = result_user.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{schema.email} does not exist")
    if not activ_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid token entered")
    if user.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You are already active")

    user.is_active = True
    await session.commit()
    return {"detail": "Activation successful"}


@router.post("/password-reset/request", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def user_password_reset(schema: TokenResetPasswordRequest, session: AsyncSession = Depends(get_db)):
    user_stmt = select(UserModel).where(UserModel.email == schema.email)
    user_result = await session.execute(user_stmt)
    db_user = user_result.scalars().first()

    if not db_user or not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password"
        )

    if not db_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not active")
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email")

    await session.execute(delete(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == db_user.id))
    try:
        new_token = PasswordResetTokenModel(user_id=db_user.id)
        session.add(new_token)
        await session.commit()
        print("new_tokennn", new_token.token)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e)

    return {"message": "Request successful"}


@router.post("/password-reset/complete")
async def user(schema: TokenResetPasswordCompleteRequest, session: AsyncSession = Depends(get_db)):
    stmt_user = select(UserModel).where(UserModel.email == schema.email)
    result_user = await session.execute(stmt_user)
    db_user = result_user.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password")

    stmt_reset_token = select(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == db_user.id)
    result_token = await session.execute(stmt_reset_token)
    reset_token = result_token.scalars().first()

    if not reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password")

    if reset_token.token != schema.token:
        delete_query = delete(RefreshTokenModel).where(RefreshTokenModel.user_id == db_user.id)
        await session.execute(delete_query)
        await session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    current_time = datetime.now(timezone.utc)
    if reset_token.expires_at.replace(tzinfo=timezone.utc) < current_time:
        delete_query = delete(RefreshTokenModel).where(RefreshTokenModel.user_id == db_user.id)
        await session.execute(delete_query)
        await session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token time expired")

    try:
        db_user._hashed_password = password_hash_pwd(password_validator_func(schema.password))
        delete_query = delete(RefreshTokenModel).where(RefreshTokenModel.user_id == db_user.id)
        await session.execute(delete_query)
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during user creation. -- {e}"
        )

    return {
        "message": "password successfully changed"
    }


@router.post("/login/", response_model=UserLoginResponse)
async def user_login(
        session: AsyncSession = Depends(get_db),
        form_data: OAuth2PasswordRequestForm = Depends()
):
    email = form_data.username
    password = form_data.password

    stmt_user = select(UserModel).where(UserModel.email == email)
    result_user = await session.execute(stmt_user)
    db_user = result_user.scalars().first()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not db_user.is_active or not db_user.verify_password_pwd(password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    refresh = create_refresh_token({"sub": str(db_user.id)})
    try:
        refresh_token = RefreshTokenModel(
            user_id=db_user.id,
            token=refresh
        )

        session.add(refresh_token)
        await session.commit()

    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during user creation. -- {e}"
        )

    access = create_access_token({"sub": str(db_user.id)})
    return {
        "access_token": access,
        "refresh_token": refresh_token.token
    }


@router.post("/logout/", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
        current_user: Annotated[UserModel, Depends(get_current_user)],
        token: str = Depends(get_user_token),
        session: AsyncSession = Depends(get_db)
):
    current_time = datetime.now(timezone.utc)

    stmt = select(RefreshTokenModel).where(RefreshTokenModel.user_id == current_user.id)
    refresh_result = await session.execute(stmt)
    refresh = refresh_result.scalars().first()
    if not authenticate_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")
    if refresh.expires_at < current_time:
        await session.delete(refresh)
        await session.commit()
        return {
            "token": token,
            "message": "Session expired and token removed"
        }

    await session.delete(refresh)
    await session.commit()

    return {"message": "Logged out successfully"}


@router.post("/refresh/", response_model=AccessTokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
        token_data: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db),
):
    try:
        decoded_token = decode_token(token_data.refresh_token)
        user_id = decoded_token.get("sub")
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    stmt = select(RefreshTokenModel).filter_by(token=token_data.refresh_token)
    result = await db.execute(stmt)
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

    new_access_token = create_access_token({"sub": str(user_id)})

    return AccessTokenResponse(access_token=new_access_token)
