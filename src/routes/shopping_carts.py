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
        CartItemsModel.cart_id == cart.id,
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


@router.delete("/{cart_item_id}/delete/")
async def remove_cart_item(
        cart_item_id: int,
        current_user: UserModel = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    stmt = select(UserModel).where(UserModel.id == current_user.id)
    result: Result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stmt = select(CartItemsModel).where(CartItemsModel.cart_id == cart_item_id)
    result: Result = await session.execute(stmt)
    cart_item = result.scalars().first()

    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

    await session.delete(cart_item)
    await session.commit()

    return "Movie deleted from cart successfully"
