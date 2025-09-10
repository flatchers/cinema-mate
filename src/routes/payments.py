import json
from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_filter import FilterDepends
from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from starlette import status
from starlette.responses import JSONResponse
from stripe import SignatureVerificationError

from src.database.models import UserModel, PaymentModel, OrderModel, OrderItemModel
from src.database.models.accounts import UserGroupEnum
from src.database.models.order import StatusEnum
from src.database.models.payments import PaymentStatus, PaymentItemModel
from src.database import get_db
from src.notifications.send_email.send_payment_confirmation import (
    send_payment_confirmation_email,
)
from src.querying.payment_filtering import PaymentFilter
from src.security.token_manipulation import get_current_user
from src.config.settings import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()

DOMAIN = "http://127.0.0.1:8000"


@router.post(
    "/add/{order_id}/",
    summary="Create payment",
    description=(
        "<h3>Create a new payment via the Stripe payment system</h3>"
        "<p>Creates a new payment if one "
        "does not already exist. If a payment "
        "already exists, a <code>409 Conflict</code> is returned.</p>"
        "<p>Upon successful creation, the user "
        "is redirected to the Stripe Checkout page.</p>"
    ),
    responses={
        201: {
            "description": "Payment was created successful "
            "and redirected to the Stripe Checkout page",
            "content": {
                "application/json": {
                    "example": {"response": "payment add successfully"}
                }
            },
        },
        404: {
            "description": "If the order does not exist "
            "or does not belong to the current user.",
            "content": {"application/json": {"example": {"detail": "Order not found"}}},
        },
        409: {
            "description": "If the payment already exist for the order.",
            "content": {
                "application/json": {"example": {"detail": "payment already exist"}}
            },
        },
    },
    status_code=status.HTTP_201_CREATED,
)
async def payment_add(
    order_id: int,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Creates a Stripe checkout session for the
    specified order and saves payment details in the database.

    Validates that the order exists and belongs to
    the current user, and that no payment has been previously created.
    If valid, creates a new payment record along with
    a Stripe checkout session including order item details.

    Args:
        order_id (int): The ID of the order for
        which the payment is created.
        current_user (UserModel): The currently
        authenticated user (injected via Depends).
        session (AsyncSession): The async database
        session (injected via Depends).

    Raises:
        HTTPException 404: If the order does not
        exist or does not belong to the current user.
        HTTPException 409: If a payment already exists for the order.

    Returns:
        dict: JSON response containing a confirmation message
        of successful payment creation.

    Side Effects:
        - Creates a new PaymentModel record.
        - Creates PaymentItemModel records for each order item
        with the price at the time of the order.
        - Initiates a Stripe Checkout session and
        logs payment ID and payment URL to the console.
    """
    stmt = (
        select(OrderModel)
        .options(
            selectinload(OrderModel.order_items).selectinload(OrderItemModel.movie)
        )
        .where(
            OrderModel.id == order_id,
            OrderModel.user_id == current_user.id,
        )
    )
    result = await session.execute(stmt)
    order = result.scalars().first()

    if not order or order.status != StatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    stmt_payment = select(PaymentModel).where(PaymentModel.order_id == order_id)
    result_payment: Result = await session.execute(stmt_payment)
    payment = result_payment.scalars().first()

    if payment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="payment already exist"
        )

    checkout_session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": ", ".join(
                            [item.movie.name for item in order.order_items]
                        )
                    },
                    "unit_amount": int(Decimal(str(order.total_amount)) * 100),
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
        external_payment_id=checkout_session["id"],
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

    return {"response": "payment add successfully"}


@router.get(
    "/successful/",
    summary="payment successful response",
    description="This endpoint is called if the `my_webhook_view` "
    "function returns status code 200. "
    "It confirms that the order has been paid successfully.",
    responses={
        200: {
            "description": "Order is paid, payment was successful",
            "content": {
                "application/json": {"example": {"response": "payment was successful"}}
            },
        }
    },
    status_code=200,
)
async def successful_payment():
    """
    Returns a confirmation response when the payment was successful.
    """
    return {"response": "payment was successful"}


@router.get(
    "/cancel/",
    summary="Payment cancelled response",
    description="This endpoint is called if "
    "the payment was cancelled or failed. "
    "It confirms that the payment process did not complete.",
    responses={
        200: {
            "description": "Payment was cancelled or failed",
            "content": {
                "application/json": {"example": {"response": "payment failed"}}
            },
        },
    },
    status_code=status.HTTP_200_OK,
)
async def cancel_payment():
    """
    Returns a response indicating that the payment was cancelled or failed.
    """
    return {"response": "payment failed"}


@router.post(
    "/webhook/",
    summary="The stripe webhook",
    description=(
        "Receives and processes events from Stripe. "
        "Validates payload and signature if "
        "`WEBHOOK_ENDPOINT_SECRET` is set. "
        "Returns 200 if the event is successfully handled, "
        "or raises 400 in case of invalid payload/signature."
    ),
    responses={
        200: {
            "description": "Event is successfully handled.",
            "content": {"application/json": {"example": {"response": "Successful"}}},
        },
        400: {"description": "Invalid payload or signature"},
    },
    status_code=status.HTTP_200_OK,
)
async def my_webhook_view(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Stripe webhook endpoint.

    Receives events from Stripe, validates payload
    and signature (if WEBHOOK_ENDPOINT_SECRET is set),
    and processes different types of events such as payment success or failure.

    :param request: FastAPI Request object containing
    the raw webhook payload and headers.
    :param db: Async SQLAlchemy session, used
    to update order/payment status in the database.
    :return: JSON response indicating success, e.g., {"status": "success"}.
             If the payload is invalid or signature verification fails,
             raises HTTPException with status 400.
    """
    payload = await request.body()
    event = None

    try:
        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except ValueError as e:
        # Invalid payload
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error: {e}"
        )

    if settings.WEBHOOK_ENDPOINT_SECRET:
        # Only verify the event if you've defined an endpoint secret
        # Otherwise, use the basic event deserialized with JSON
        sig_header = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.WEBHOOK_ENDPOINT_SECRET
            )
        except SignatureVerificationError as e:
            print("⚠️  Webhook signature verification failed." + str(e))
            return JSONResponse(status_code=400, content={"success": False})

    # Handle the event
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object  # contains a stripe.PaymentIntent
        payment_id = payment_intent["id"]
        stmt = (
            select(PaymentModel)
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
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            send_payment_confirmation_email(user.email)
            await db.commit()

        print(f"✅ PaymentIntent succeeded: {payment_intent['id']}")
    # Then define and call a method to handle the successful payment intent.
    # handle_payment_intent_succeeded(payment_intent)
    elif event.type == "payment_intent.canceled":
        payment_intent = event.data.object
        payment_id = payment_intent["id"]
        cancellation_reason = payment_intent.get("cancellation_reason", "unspecified")
        stmt_payment = (
            select(PaymentModel)
            .options(selectinload(PaymentModel.user))
            .options(selectinload(PaymentModel.order))
            .where(PaymentModel.external_payment_id == payment_id)
        )
        result_payment: Result = await db.execute(stmt_payment)
        payment = result_payment.scalars().first()

        if payment:
            payment.status = PaymentStatus.CANCELED
            await db.commit()

        print(
            f"⚠️ PaymentIntent canceled: {payment_id}, " f"reason: {cancellation_reason}"
        )
        return {
            "status": event.type,
            "payment_id": payment_id,
            "reason": cancellation_reason,
        }
    elif event.type == "checkout.session.completed":
        session = event.data.object
        checkout_id = session["id"]
        stmt_payment_session = (
            select(PaymentModel)
            .options(selectinload(PaymentModel.user))
            .options(selectinload(PaymentModel.order))
            .where(PaymentModel.external_payment_id == checkout_id)
        )
        result_payment_session: Result = await db.execute(stmt_payment_session)
        payment = result_payment_session.scalars().first()

        if payment:
            payment.status = PaymentStatus.SUCCESSFUL
            payment.order.status = StatusEnum.PAID
            stmt_user = (
                select(UserModel)
                .join(PaymentModel)
                .where(UserModel.id == payment.user_id)
            )
            result_user: Result = await db.execute(stmt_user)
            current_user = result_user.scalars().first()

            if not current_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            send_payment_confirmation_email(current_user.email)
            await db.commit()
            print(f"✅ Checkout session completed: {checkout_id}")

    else:
        print(f"⚠️ Unhandled event type: {event.type}")
        return {"response": f"Unhandled event type: {event.type}"}

    return {"response": "Successful"}


@router.post(
    "/refund/{external_payment_id}/",
    summary="Payment refund",
    description=(
        "<h3>Receives and processes refund event</h3>"
        "<p>Creates refund event, validates external "
        "payment id, changes payment status-> REFUND</p>"
        "<p>If 200 if the event successfully handled "
        "or raises 400 error in case of entering invalid data</p>"
    ),
    responses={
        200: {
            "description": "Refund",
            "content": {
                "application/json": {"example": {"response": "Refund Successful"}}
            },
        },
        400: {"description": "Invalid entering data"},
    },
    status_code=status.HTTP_200_OK,
)
async def payment_refund(
    external_payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Refunds a payment through the payment provider (e.g., Stripe).

    This endpoint attempts to refund a previously completed payment based on
    its external identifier. Only the authenticated user associated with the
    payment can request a refund.

    :param external_payment_id: External payment ID to be refunded.
    :param db: Async SQLAlchemy session.
    :param current_user: Authenticated user requesting the refund.
    Retrieved via dependency injection.
    :return: JSON response confirming message.
    """
    stmt = select(PaymentModel).where(
        PaymentModel.user_id == current_user.id,
        PaymentModel.external_payment_id == external_payment_id,
    )
    result: Result = await db.execute(stmt)
    payment = result.scalars().first()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    try:
        session = stripe.checkout.Session.retrieve(external_payment_id)
        raw_payment_intent = session.payment_intent
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to retrieve Stripe session: {str(e)}"
        )
    if isinstance(raw_payment_intent, str):

        refund = stripe.Refund.create(
            payment_intent=raw_payment_intent, amount=int(payment.amount) * 100
        )
        if refund.status == "succeeded":
            payment.status = PaymentStatus.REFUNDED

            await db.commit()
        else:
            raise HTTPException(status_code=400, detail="Refund failed")

    return {"response": "Refund Successful"}


@router.get(
    "/history/",
    summary="Payment list",
    description="Returns list of payment of currently user",
    responses={
        200: {
            "description": "shows all payments",
            "content": {
                "application/json": {
                    "example": {
                        "response": [
                            {
                                "id": 1,
                                "amount": 49.99,
                                "currency": "usd",
                                "status": "succeeded",
                                "created_at": "2025-09-05T12:00:00Z",
                            },
                            {
                                "id": 2,
                                "amount": 15.00,
                                "currency": "usd",
                                "status": "refunded",
                                "created_at": "2025-09-04T10:30:00Z",
                            },
                        ]
                    }
                }
            },
        },
        400: {"description": "Invalid entering data"},
    },
    status_code=status.HTTP_200_OK,
)
async def payment_list(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the list of payments for the currently authenticated user.

    :param current_user: The authenticated user (retrieved from JWT/session).
    :param db: Async SQLAlchemy session used to query the database.
    :return: Dictionary with a list of payments,
    """
    stmt = select(PaymentModel).where(PaymentModel.user_id == current_user.id)
    result: Result = await db.execute(stmt)
    payments = result.scalars().all()
    if not payments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No payments")

    return {"response": payments}


@router.get(
    "/moderator/list/",
    summary="Payment List (must be a moderator)",
    description=(
        "<h3>Moderators can see payment list by user ID</h3>"
        "<p>This endpoint allows moderators to "
        "retrieve payment history of a specific user. "
        "Supports filtering via query parameters.</p>"
    ),
    responses={
        200: {
            "description": "List of payments for the requested user.",
        },
        403: {
            "description": "Access denied.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Access forbidden for "
                        "{user.group.name}: "
                        "insufficient permissions."
                    }
                }
            },
        },
    },
    status_code=status.HTTP_200_OK,
)
async def payment_list_for_moderator(
    payment_filter: PaymentFilter = FilterDepends(PaymentFilter),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """

    Returns a list of payments filtered by user ID or other parameters.
    Accessible only to users with moderator privileges.

    :param payment_filter: Filtering options for payments
    :param current_user: The authenticated user making the request.
    :param db: Async SQLAlchemy session used to query payment data.
    :return: Dictionary containing a list of payments for the requested user
    """
    stmt_user = (
        select(UserModel)
        .options(joinedload(UserModel.group))
        .where(UserModel.id == current_user.id)
    )
    result_user: Result = await db.execute(stmt_user)
    user = result_user.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.group or user.group.name != UserGroupEnum.MODERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden for {user.group.name}: "
            "insufficient permissions.",
        )

    stmt_payment = payment_filter.filter(select(PaymentModel))
    result_payment: Result = await db.execute(stmt_payment)
    payments = result_payment.scalars().all()

    return {"response": payments}
