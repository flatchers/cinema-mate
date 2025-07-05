from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from src.database.models import UserModel, Movie, CartItemsModel, CartModel
from src.database.session_sqlite import get_db
from src.security.token_manipulation import get_current_user

router = APIRouter()


@router.post("/{movie_id}/add/")
async def add_cart_item(
        movie_id: int,
        current_user: UserModel = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    stmt = select(UserModel).options(selectinload(UserModel.cart)).where(UserModel.id == current_user.id)
    result: Result = await session.execute(stmt)
    user = result.scalars().first()
    # user = await session.get(UserModel, current_user.id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    cart = user.cart
    if not user.cart:
        cart = CartModel(
            user_id=user.id,
        )
        session.add(cart)
        await session.flush()

    movie = await session.get(Movie, movie_id)

    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

    stmt = select(CartItemsModel).where(
        CartItemsModel.id == cart.id,
        CartItemsModel.movie_id == movie_id
    )
    existing = await session.execute(stmt)

    if existing.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Movie already in cart")

    cart_item = CartItemsModel(
        cart_id=cart.id,
        movie_id=movie_id
    )
    session.add(cart_item)
    await session.commit()

    return cart_item





