from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.accounts import UserModel, UserGroup, UserGroupEnum, ActivationTokenModel, \
    PasswordResetTokenModel, RefreshTokenModel
from src.database.session_sqlite import get_db
from src.schemas.accounts import UserCreateResponse, UserCreateRequest, TokenActivationRequest, \
    TokenResetPasswordRequest, UserLoginRequest, UserLoginResponse
from src.security.token_manipulation import create_refresh_token, create_access_token
from src.security.validations import verify_password

router = APIRouter()


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


@router.post("/password-reset/request/", status_code=status.HTTP_200_OK)
async def user_password_reset(schema: TokenResetPasswordRequest, session: AsyncSession = Depends(get_db)):
    user_stmt = select(UserModel).where(UserModel.email == schema.email)
    user_result = await session.execute(user_stmt)
    user = user_result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not active")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email")

    await session.execute(delete(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id))

    new_token = PasswordResetTokenModel(user_id=user.id)

    session.add(new_token)
    await session.commit()
    print("new_tokennn", new_token.token)

    return {"message": "Request successful"}


@router.post("/login/", response_model=UserLoginResponse)
async def user_login(schema: UserLoginRequest, session: AsyncSession = Depends(get_db)):
    stmt_user = select(UserModel).where(UserModel.email == schema.email)
    result_user = await session.execute(stmt_user)
    user = result_user.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active or not user.verify_password_pwd(schema.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    refresh = create_refresh_token({"user_id": user.id})
    try:
        refresh_token = RefreshTokenModel(
            user_id=user.id,
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

    access = create_access_token({"user_id": user.id})
    return {
        "access_token": refresh_token.token,
        "refresh_token": access
    }
