import json

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, DECIMAL, Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status
from starlette.responses import JSONResponse

from src.database.models import UserModel, PaymentModel, OrderModel, OrderItemModel
from src.database.models.order import StatusEnum
from src.database.models.payments import PaymentStatus, PaymentItemModel
from src.database.session_sqlite import get_db
from src.notifications.send_email.send_payment_confirmation import send_payment_confirmation_email
from src.schemas.payments import StripeRequestSchema
from src.security import stripe_keys
from src.security.stripe_keys import WEBHOOK_ENDPOINT_SECRET
from src.security.token_manipulation import get_current_user

stripe.api_key = stripe_keys.STRIPE_SECRET_KEY

router = APIRouter()

DOMAIN = "http://127.0.0.1:8000"


@router.post("/add/{order_id}/", status_code=status.HTTP_200_OK)
async def payment_add(
        order_id: int,
        current_user: UserModel = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Creates a Stripe checkout session for the specified order and saves payment details in the database.

    Validates that the order exists and belongs to the current user, and that no payment has been previously created.
    If valid, creates a new payment record along with a Stripe checkout session including order item details.

    Args:
        order_id (int): The ID of the order for which the payment is created.
        current_user (UserModel): The currently authenticated user (injected via Depends).
        session (AsyncSession): The async database session (injected via Depends).

    Raises:
        HTTPException 404: If the order does not exist or does not belong to the current user.
        HTTPException 409: If a payment already exists for the order.

    Returns:
        dict: JSON response containing a confirmation message of successful payment creation.

    Side Effects:
        - Creates a new PaymentModel record.
        - Creates PaymentItemModel records for each order item with the price at the time of the order.
        - Initiates a Stripe Checkout session and logs payment ID and payment URL to the console.
    """
    stmt = (
        select(OrderModel)
        .options(selectinload(OrderModel.order_items).selectinload(OrderItemModel.movie))
        .where(OrderModel.id == order_id, OrderModel.user_id == current_user.id)
    )
    result = await session.execute(stmt)
    order = result.scalars().first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    stmt = select(PaymentModel).where(
        PaymentModel.order_id == order_id
    )
    result: Result = await session.execute(stmt)
    payment = result.scalars().first()

    if payment:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payment already exist")

    checkout_session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": ", ".join([item.movie.name for item in order.order_items])
                    },
                    "unit_amount": int(order.total_amount) * 100,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=DOMAIN + "/api/v1/payments/successful/",
        cancel_url=DOMAIN + "/api/v1/payments/cancel/",
    )

    new_payment = PaymentModel(
        user_id=current_user.id,
        order_id=order_id,
        amount=order.total_amount,
        external_payment_id=checkout_session["id"]
    )
    session.add(new_payment)
    await session.flush()

    for item in order.order_items:
        new_payment_id = PaymentItemModel(
            payment_id=new_payment.id,
            order_item_id=item.id,
            price_at_payment=item.price_at_order,
        )
        session.add(new_payment_id)
    await session.commit()
    print("payment_id: ", checkout_session["id"])
    print("payment_url: ", checkout_session["url"])

    return {
        "response": "payment add successfully"
    }


@router.get("/successful/")
async def successful_payment():
    return {"response": "payment was successful"}


@router.get("/cancel/")
async def cancel_payment():
    return {"response": "payment failed"}
