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


@router.post("/add/{order_id}/", status_code=status.HTTP_201_CREATED)
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
        .where(
            OrderModel.id == order_id,
            OrderModel.user_id == current_user.id,
        )
    )
    result = await session.execute(stmt)
    order = result.scalars().first()

    if not order or order.status != StatusEnum.PENDING:
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


@router.post("/webhook/", status_code=status.HTTP_200_OK)
async def my_webhook_view(
        request: Request,
        db: AsyncSession = Depends(get_db)
):
    payload = await request.body()
    event = None

    try:
        event = stripe.Event.construct_from(
            json.loads(payload), stripe.api_key
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error: {e}")

    if WEBHOOK_ENDPOINT_SECRET:
        # Only verify the event if you've defined an endpoint secret
        # Otherwise, use the basic event deserialized with JSON
        sig_header = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, WEBHOOK_ENDPOINT_SECRET
            )
        except stripe.error.SignatureVerificationError as e:
            print('⚠️  Webhook signature verification failed.' + str(e))
            return JSONResponse(status_code=400, content={"success": False})

    # Handle the event
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object  # contains a stripe.PaymentIntent
        payment_id = payment_intent["id"]
        stmt = (select(PaymentModel)
                .options(selectinload(PaymentModel.user))
                .options(selectinload(PaymentModel.order))
                .where(PaymentModel.external_payment_id == payment_id)
                )
        result: Result = await db.execute(stmt)
        payment = result.scalars().first()

        if payment:
            payment.status = PaymentStatus.SUCCESSFUL
            payment.order.status = StatusEnum.PAID
            user = await db.get(UserModel, payment.user_id)
            send_payment_confirmation_email(user.email)
            await db.commit()

        print(f"✅ PaymentIntent succeeded: {payment_intent['id']}")
    # Then define and call a method to handle the successful payment intent.
    # handle_payment_intent_succeeded(payment_intent)
    elif event.type == "payment_intent.canceled":
        payment_intent = event.data.object
        payment_id = payment_intent["id"]
        cancellation_reason = payment_intent.get("cancellation_reason", "unspecified")
        stmt = (select(PaymentModel)
                .options(selectinload(PaymentModel.user))
                .options(selectinload(PaymentModel.order))
                .where(PaymentModel.external_payment_id == payment_id)
                )
        result: Result = await db.execute(stmt)
        payment = result.scalars().first()

        if payment:
            payment.status = PaymentStatus.CANCELED
            await db.commit()

        print(f"⚠️ PaymentIntent canceled: {payment_id}, reason: {cancellation_reason}")
        return {"status": event.type,
                "payment_id": payment_id,
                "reason": cancellation_reason
                }
    elif event.type == "checkout.session.completed":
        session = event.data.object
        checkout_id = session["id"]
        stmt = (select(PaymentModel)
                .options(selectinload(PaymentModel.user))
                .options(selectinload(PaymentModel.order))
                .where(PaymentModel.external_payment_id == checkout_id)
                )
        result: Result = await db.execute(stmt)
        payment = result.scalars().first()

        if payment:
            payment.status = PaymentStatus.SUCCESSFUL
            payment.order.status = StatusEnum.PAID
            stmt = select(UserModel).join(PaymentModel).where(UserModel.id == payment.user_id)
            result: Result = await db.execute(stmt)
            current_user = result.scalars().first()
            send_payment_confirmation_email(current_user.email)
            await db.commit()
            print(f"✅ Checkout session completed: {checkout_id}")

    else:
        print(f"⚠️ Unhandled event type: {event.type}")
        return {"response": f"Unhandled event type: {event.type}"}

    return {"response": "Successful"}


@router.post("/refund/{external_payment_id}/", status_code=status.HTTP_200_OK)
async def payment_refund(
        external_payment_id: str,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    stmt = select(PaymentModel).where(
        PaymentModel.user_id == current_user.id,
        PaymentModel.external_payment_id == external_payment_id
    )
    result: Result = await db.execute(stmt)
    payment = result.scalars().first()

    try:
        session = stripe.checkout.Session.retrieve(external_payment_id)
        payment_intent_id = session.payment_intent
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to retrieve Stripe session: {str(e)}")

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    refund = stripe.Refund.create(
        payment_intent=payment_intent_id,
        amount=int(payment.amount) * 100
    )
    if refund.status == "succeeded":
        payment.status = PaymentStatus.REFUNDED

        await db.commit()
    else:
        raise HTTPException(status_code=400, detail="Refund failed")

    return {"response": "Refund Successful"}
