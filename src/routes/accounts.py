from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.accounts import UserModel, UserGroup, UserGroupEnum, ActivationTokenModel
from src.database.session_sqlite import get_db
from src.schemas.accounts import UserCreateResponse, UserCreateRequest

router = APIRouter()


@router.post("/register", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def user_registration(schema: UserCreateRequest, session: AsyncSession = Depends(get_db)):

    stmt_email = select(UserModel).where(UserModel.email == schema.email)
    result_email = await session.execute(stmt_email)
    user_email = result_email.scalars().first()

    stmt_group = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    result_group = await session.execute(stmt_group)
    user_group = result_group.scalars().first()

    if user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
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

    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during user creation. -- {e}"
        ) from e

    return new_user
