from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from src.database.models import UserModel, Movie, CartItemsModel, CartModel
from src.database.models.accounts import UserGroupEnum, UserGroup
from src.database.models.shopping_cart import NotificationDeleteModel
from src.database import get_db
from src.schemas.shopping_carts import MovieOut, MovieListResponse
from src.security.token_manipulation import get_current_user

router = APIRouter()


@router.post(
    "/{movie_id}/add/",
    summary="Add cart item",
    description="Create cart and cart item to the database for currently user",
    responses={
        201: {
            "description": "Movie successfully added to the user's cart.",
            "content":
                {
                    "application/json": {
                        "example": {"message": "Movie added to cart"}
                    }
                },
        },
        404: {
            "description": "Movie or user does not exist in the database.",
            "content": {
                "application/json": {
                    "example": {
                        "user_not_found": {"value": {"detail": "User not found"}},
                        "movie_not_found": {"value": {"detail": "Movie not found"}}
                    }
                }
            }
        },
        409: {
            "description": "Trying add to the database already existing cart item",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie already in cart"}
                }
            }
        }
    },
    status_code=201
)
async def add_cart_item(
        movie_id: int,
        current_user: UserModel = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Add a movie to the user's shopping cart.

    :param movie_id: The unique id of the movie to add.
    :type movie_id: int
    :param current_user: The currently authenticated user.
    :type current_user: UserModel
    :param session: The database session.
    :type session: AsyncSession
    :return: Cart item details.
    :rtype: dict
    """
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

    return {"create cart item": cart_item}


@router.delete(
    "/{cart_item_id}/delete/",
    summary="Remove cart item",
    description=(
            "<h3>Remove specific cart item from database by its unique ID</h3>"
            "if cart item exist, it will be deleted, if it doesn't exist, "
            "a 404 error will be returned"
    ),
    responses={
        204: {
            "description": "Successful deleted from the database",
            "content": {
                "application/json": {
                    "example": {"message": "Movie deleted from cart successfully"}
                }
            }
        },
        404: {
            "description": "Movie or user does not exist in the database.",
            "content": {
                "application/json": {
                    "example": {
                        "user_not_found": {"value": {"detail": "User not found"}},
                        "movie_not_found": {"value": {"detail": "Movie not found"}}
                    }
                }
            }
        },
    },
    status_code=204
)
async def remove_cart_item(
        cart_item_id: int,
        current_user: UserModel = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Remove cart item by its ID

    :param cart_item_id: The unique id of the movie to delete.
    :type cart_item_id: int
    :param current_user: The currently authenticated user.
    :type current_user: UserModel
    :param session: The database session.
    :type session: AsyncSession
    :return: message of successful deleted cart item from database
    :rtype: dict
    """
    stmt = select(UserModel).where(UserModel.id == current_user.id)
    result: Result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stmt = select(CartItemsModel).where(CartItemsModel.movie_id == cart_item_id)
    result: Result = await session.execute(stmt)
    cart_item = result.scalars().first()

    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")

    stmt = select(UserModel).join(UserModel.group).where(user.group == UserGroupEnum.MODERATOR)
    result: Result = await session.execute(stmt)
    moderator_user = result.scalars().all()

    cart_item_id = cart_item.id

    await session.delete(cart_item)

    notif = NotificationDeleteModel(
        cart_items_id=cart_item_id,
        comment=f"user {user.email} with id {user.id} deleted item {cart_item}",
    )
    notif.users.extend(moderator_user)
    session.add(notif)

    await session.commit()

    return {"message": "Movie deleted from cart successfully"}


@router.get(
    "/list/",
    response_model=MovieListResponse,
    summary="Cart list",
    description="<h3>Shows the list of cart items in the cart</h3>",
    responses={
        200: {
            "description": "Successful request",
        },
        404: {
            "description": "Movie or user does not exist in the database.",
            "content": {
                "application/json": {
                    "example": {
                        "user_not_found": {"value": {"detail": "User not found"}},
                        "movie_not_found": {"value": {"detail": "Movie not found"}}
                    }
                }
            }
        },
    },
    status_code=200
)
async def cart_list(
        current_user: UserModel = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Returns a list of movies found in the cart.

    :param current_user: The currently authenticated user
    :type current_user: UserModel.
    :param session: The database session.
    :type session: AsyncSession
    :return: MovieListResponse object containing a list of movies in the cart
    :rtype: MovieListResponse
    """
    stmt = select(UserModel).where(UserModel.id == current_user.id)
    result: Result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stmt = (
        select(CartModel)
        .options(selectinload(CartModel.cart_items)
                 .selectinload(CartItemsModel.movie)
                 .selectinload(Movie.genres))
        .where(CartModel.user_id == user.id)
    )
    result: Result = await session.execute(stmt)
    carts = result.scalars().first()

    if not carts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="list is empty")

    movie_list = []
    for i in carts.cart_items:
        movie = i.movie
        movie_list.append(MovieOut(
            title=movie.name,
            price=movie.price,
            genres=[genre.name for genre in movie.genres],
            year=movie.year
        ))

    return MovieListResponse(movies=movie_list)


@router.get(
    "/{user_id}/detail/",
    summary="Cart item detail",
    description="Returns a list of cart items with detailed information of the user.",
    responses={
        200: {
            "description": "Returns dict with information."
        },
        404: {
            "description": "The user does not exist in database",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found"}
                }
            }
        },
        403: {
            "description": "The function is available only for admins.",
            "content": {
                "application/json": {
                    "example": {"detail": "This function for admins"}
                }
            }
        }
    },
    status_code=status.HTTP_200_OK
)
async def items_detail(
        user_id: int,
        current_user: UserModel = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
):
    """
    Returns detailed information of the specified user by its ID

    :param user_id: The unique id of the user to show.
    :type user_id: int
    :param current_user: The currently authenticated user (must be admin!)
    :type current_user: UserModel
    :param session: The database session
    :type session: AsyncSession
    :return: Dictionary containing detailed information of the selected user's cart items
    :rtype: dict
    """
    stmt = select(UserModel).options(selectinload(UserModel.group)).where(UserModel.id == current_user.id)
    result: Result = await session.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This function for admins")

    stmt = select(CartItemsModel).join(CartModel).where(CartModel.user_id == user_id)
    result: Result = await session.execute(stmt)
    purpose_user = result.scalars().all()

    return {"detail": purpose_user}
