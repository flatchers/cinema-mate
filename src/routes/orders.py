from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.functions import count
from starlette import status

from src.database.models import UserModel, CartItemsModel, CartModel, OrderModel, OrderItemModel
from src.database.session_sqlite import get_db
from src.schemas.orders import OrderSchemaResponse
from src.security.token_manipulation import get_current_user

router = APIRouter()


@router.post("/add/")
async def create_order(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):

    stmt = (
        select(CartModel)
        .options(selectinload(CartModel.cart_items).selectinload(CartItemsModel.movie))
        .where(CartModel.user_id == current_user.id))
    result: Result = await db.execute(stmt)
    cart = result.scalars().first()

    stmt = select(OrderItemModel).join(OrderItemModel.order).options(selectinload(OrderItemModel.movie)).where(OrderModel.user_id == current_user.id)
    result: Result = await db.execute(stmt)
    order_item_all = result.scalars().all()

    if not cart or not cart.cart_items:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Your cart is empty")
    existing_movie_ids = {i.movie_id for i in order_item_all}
    existing_films = []
    new_added_films = []
    new_added_films_names = []

    for item in cart.cart_items:
        if item.movie_id in existing_movie_ids:
            existing_films.append(item.movie.name)
        else:
            new_added_films.append(item)
            new_added_films_names.append(item.movie.name)
    if new_added_films:
        order = OrderModel(
            user_id=current_user.id,
            total_amount=sum(item.movie.price for item in new_added_films)
        )
        db.add(order)
        await db.flush()

        for item in new_added_films:
            order_items = OrderItemModel(
                order_id=order.id,
                movie_id=item.movie_id,
                price_at_order=item.movie.price,
            )
            db.add(order_items)

    for item in cart.cart_items:
        await db.delete(item)

    await db.commit()

    if existing_films and new_added_films_names:
        str_existing_films = ", ".join(existing_films)
        str_new_films = ", ".join(new_added_films_names)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{str_existing_films} already exist, "
                   f"{str_new_films} was added to order")

    if existing_films:
        str_existing_films = ", ".join(existing_films)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{str_existing_films} already exist"
        )

    return {"response": "Order created successfully"}


@router.get("/list/", response_model=List[OrderSchemaResponse])
async def order_list(
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    stmt = select(OrderModel).options(selectinload(OrderModel.order_items)).where(OrderModel.user_id == current_user.id)
    result: Result = await db.execute(stmt)
    orders = result.scalars().all()

    return [
        OrderSchemaResponse(
            created_at=order.created_at,
            count_films=len(order.order_items),
            total_amount=order.total_amount,
            status=order.status
        )
        for order in orders
    ]
