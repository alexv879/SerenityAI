"""
Twilio Pay Integration - Payment Collection Handler

Handles payment collection via Twilio Pay when 5-minute trial expires.
Integrates with Stripe for payment processing.
"""

from fastapi import APIRouter, Request, HTTPException, Response
from twilio.twiml.voice_response import VoiceResponse, Pay
import stripe
import os
from starlette.concurrency import run_in_threadpool

from utils.subscription_manager import get_subscription_manager
from twilio.request_validator import RequestValidator
import config

router = APIRouter()

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
VOICE = "Polly.Amy-Neural"


@router.post("/payment/trigger")
async def trigger_payment_collection(request: Request):
    """
    Called at 4:30 mark of trial to initiate payment

    Returns TwiML with <Pay> verb for card collection
    """
    form = await request.form()
    call_sid = form.get("CallSid")
    phone = form.get("From")

    # Check if already has active subscription
    subscription_mgr = await get_subscription_manager()
    subscription = await subscription_mgr.check_active_subscription(phone)
    if subscription["active"]:
        # Already paid, continue conversation
        response = VoiceResponse()
        response.say(
            "Welcome back! Let's continue our chat.",
            voice=VOICE
        )
        response.redirect("/voice/entry")
        return Response(content=str(response), media_type="application/xml")

    # Store expected payment amount in Redis for validation
    expected_amount = "6.00"
    redis_client = await subscription_mgr._get_client()
    payment_key = f"payment:{call_sid}:expected_amount"
    await redis_client.set(payment_key, expected_amount, ex=300)  # 5 minute expiry

    # Initiate Twilio Pay
    response = VoiceResponse()

    pay = Pay(
        charge_amount=expected_amount,
        currency="GBP",
        payment_connector=config.TWILIO_PAY_CONNECTOR_NAME,  # From config/env
        status_callback="/payment/complete",
        timeout=120  # 2 minutes to enter card
    )

    # Voice prompts for card entry
    pay.prompt().say(
        "To continue chatting, I need to collect payment. "
        "It's just 10 pence per minute, or 6 pounds for a full hour. "
        "Please enter your 16-digit card number, then press star.",
        voice=VOICE
    )

    response.append(pay)

    # If payment fails or times out
    response.say(
        "I didn't receive your payment. "
        "Thank you for trying Serenity. Goodbye!",
        voice=VOICE
    )
    response.hangup()
    return Response(content=str(response), media_type="application/xml")


@router.post("/payment/complete")
async def handle_payment_complete(request: Request):
    """
    Webhook: Called after Twilio Pay completes (success or failure)
    Includes mandatory signature validation for security
    """
    # Get form data first
    form = await request.form()

    # Validate Twilio signature (MANDATORY for security)
    base_url = os.getenv("PUBLIC_BASE_URL")
    if not base_url:
        raise HTTPException(
            status_code=500,
            detail="PUBLIC_BASE_URL not configured - cannot validate webhook signature"
        )

    try:
        validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))
        signature = request.headers.get("X-Twilio-Signature", "")
        url = f"{base_url}/payment/complete"
        params = dict(form)

        if not validator.validate(url, params, signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    except ValueError as e:
        raise HTTPException(status_code=403, detail=f"Signature validation failed: {str(e)}")

    call_sid = form.get("CallSid")
    phone = form.get("From")
    payment_result = form.get("Result")  # "success" or "failure"
    payment_token = form.get("PaymentToken")
    payment_error = form.get("PaymentError")
    charge_amount = form.get("ChargeAmount", "0.00")  # Amount actually charged

    response = VoiceResponse()

    # Validate payment amount matches what we expected
    subscription_mgr = await get_subscription_manager()
    redis_client = await subscription_mgr._get_client()
    payment_key = f"payment:{call_sid}:expected_amount"
    expected_amount = await redis_client.get(payment_key)

    if expected_amount and expected_amount != charge_amount:
        response.say(
            "Payment amount verification failed. Please contact support.",
            voice=VOICE
        )
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    if payment_result == "success":
        # Create Stripe charge
        try:
            # Use idempotency to avoid double-charges
            idempotency_key = f"{call_sid}:{payment_token}"
            charge = await run_in_threadpool(
                stripe.Charge.create,
                amount=600,  # £6.00 in pence
                currency="gbp",
                source=payment_token,
                description=f"Serenity AI - 60 minutes - {phone}",
                idempotency_key=idempotency_key,
            )

            # Create subscription in Redis
            subscription_mgr = await get_subscription_manager()
            await subscription_mgr.create_subscription(
                phone=phone,
                payment_id=charge.id,
                minutes=60
            )

            # Log payment
            from utils.conversation_logger import get_conversation_logger
            conversation_logger = await get_conversation_logger()
            await conversation_logger.log_payment(
                phone_hash=subscription_mgr._hash_phone(phone),
                call_sid=call_sid,
                amount=6.00,
                stripe_charge_id=charge.id
            )

            response.say(
                "Payment received! You have 60 minutes to chat. "
                "Now, where were we?",
                voice=VOICE
            )
            response.redirect("/voice/entry")

        except stripe.error.CardError as e:
            response.say(
                f"Sorry, your card was declined. {e.user_message}. "
                "Please try again later. Goodbye!",
                voice=VOICE
            )
            response.hangup()

    else:
        # Payment failed
        response.say(
            f"Payment failed: {payment_error}. "
            "Thank you for trying Serenity. Goodbye!",
            voice=VOICE
        )
        response.hangup()
    return Response(content=str(response), media_type="application/xml")


@router.post("/payment/refund")
async def refund_payment(request: Request):
    """
    Admin endpoint: Refund a customer's payment

    Body: {"phone": "+447411123456", "reason": "Customer request"}
    """
    data = await request.json()
    phone = data.get("phone")
    reason = data.get("reason", "Customer request")

    # Get most recent payment
    subscription_mgr = await get_subscription_manager()
    subscription = await subscription_mgr.get_subscription(phone)
    if not subscription or not subscription.get("stripe_payment_id"):
        raise HTTPException(status_code=404, detail="No payment found")

    # Refund in Stripe
    refund = await run_in_threadpool(
        stripe.Refund.create,
        charge=subscription["stripe_payment_id"],
        reason="requested_by_customer",
        metadata={"reason": reason}
    )

    # Deactivate subscription
    await subscription_mgr.cancel_subscription(phone)

    return {
        "status": "success",
        "refund_id": refund.id,
        "amount": refund.amount / 100
    }
