from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from starlette import status

from src.database.models import (
    UserModel,
    CartItemsModel,
    CartModel,
    OrderModel,
    OrderItemModel,
)
from src.database.models.order import StatusEnum
from src.database import get_db
from src.schemas.orders import OrderSchemaResponse
from src.security.token_manipulation import get_current_user

router = APIRouter()


@router.post(
    "/add/",
    summary="Create order",
    description=(
        "<h3>Create order from added to cart cart items. </h3>"
        "Returns order if not created or error if cart is empty, "
        "all cart items is already added."
    ),
    responses={
        201: {
            "description": "Order create successfully",
            "content": {
                "application/json": {
                    "example": {"response": "Order created successfully"}
                }
            },
        },
        404: {
            "description": "Cart items not found in " "the cart for creating order.",
            "content": {
                "application/json": {"example": {"detail": "Your cart is empty"}}
            },
        },
        409: {
            "description": "All or part movies already in the existing order",
            "content": {
                "application/json": {
                    "example": {
                        "all_items_in_order": {
                            "value": {"detail": "'{FILM NAMES} already exist"}
                        },
                        "part_items_in_order": {
                            "value": {
                                "detail": "{str_existing_films} already exist."
                                " {str_new_films} was added to order"
                            }
                        },
                    }
                }
            },
        },
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Create order by cart items.

    :param db: The database session.
    :type db: AsyncSession
    :param current_user: The currently authenticated user.
    :type current_user: UserModel
    :return: Dictionary message response about successful created.
    :rtype: dict
    """
    order = None
    stmt = (
        select(CartModel)
        .options(selectinload(CartModel.cart_items).selectinload(CartItemsModel.movie))
        .where(CartModel.user_id == current_user.id)
    )
    result: Result = await db.execute(stmt)
    cart = result.scalars().first()

    stmt_order_item = (
        select(OrderItemModel)
        .join(OrderItemModel.order)
        .options(selectinload(OrderItemModel.movie))
        .where(OrderModel.user_id == current_user.id)
    )
    result_order_item: Result = await db.execute(stmt_order_item)
    order_item_all = result_order_item.scalars().all()

    if not cart or not cart.cart_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Your cart is empty"
        )
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
            total_amount=sum(item.movie.price for item in new_added_films),
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
            detail=f"{str_existing_films} already exist. "
            f"{str_new_films} was added to order",
        )

    if existing_films:
        str_existing_films = ", ".join(existing_films)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{str_existing_films} already exist.",
        )

    return {"response": "Order created successfully"}


@router.get(
    "/list/",
    response_model=List[OrderSchemaResponse],
    summary="Order list",
    description=(
        "<h3>Shows list of orders if it existing</h3>"
        "Raises 404 error if a list is empty"
    ),
    responses={
        200: {"description": "Orders successfully existing"},
        404: {
            "description": "List of orders is empty",
            "content": {
                "application/json": {"example": {"detail": "The order is empty"}}
            },
        },
    },
    status_code=200,
)
async def order_list(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Returns a list of orders

    :param db: The database session.
    :type db: AsyncSession
    :param current_user: The currently authenticated user.
    :type current_user: UserModel
    :return: OrderSchemaResponse object containing a list of orders.
    :rtype: OrderSchemaResponse
    """
    stmt = (
        select(OrderModel)
        .options(joinedload(OrderModel.order_items))
        .where(OrderModel.user_id == current_user.id)
    )
    result: Result = await db.execute(stmt)
    orders = result.unique().scalars().all()
    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="The order is empty"
        )

    return [
        OrderSchemaResponse(
            id=order.id,
            created_at=order.created_at,
            count_films=len(order.order_items),
            total_amount=order.total_amount,
            status=order.status,
        )
        for order in orders
    ]


@router.delete(
    "/delete/{order_id}/",
    summary="Delete order",
    description=(
        "<h3>Delete existing order by ID.</h3>"
        "<p>Deletes the order if order is exist. If the order "
        "with the given ID doesn't exist, a 404 error will be returned</p>"
    ),
    responses={
        204: {
            "description": "Order is deleted",
            "content": {
                "application/json": {"example": {"response": "order was canceled"}}
            },
        },
        404: {
            "description": "User or order does not exist in the database",
            "content": {
                "application/json": {
                    "example": {
                        "user_not_found": {"value": {"detail": "User not found"}},
                        "order_not_found": {"value": {"detail": "Order not found."}},
                    }
                }
            },
        },
        403: {
            "description": "User cannot delete order " "if status are PAID or CANCELED",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot delete order "
                        "with status: 'PAID' or 'CANCELED'"
                    }
                }
            },
        },
    },
    status_code=status.HTTP_204_NO_CONTENT,
)
async def order_delete(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Delete specific order by its ID.

    :param order_id: The ID of the order to delete.
    :type order_id: int
    :param db: The database session
    :type db: AsyncSession
    :param current_user: The currently authenticated user.
    :type current_user: UserModel
    :return: Dictionary containing message.
    :rtype: dict
    """
    stmt = select(UserModel).where(UserModel.id == current_user.id)
    result: Result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    stmt_order = select(OrderModel).where(
        OrderModel.id == order_id, OrderModel.user_id == current_user.id
    )
    result_order = await db.execute(stmt_order)
    order = result_order.scalars().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
        )

    if order.status != StatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete order with status: {order.status.value}",
        )
    order.status = StatusEnum.CANCELED
    await db.commit()

    return {"response": "order was canceled"}
