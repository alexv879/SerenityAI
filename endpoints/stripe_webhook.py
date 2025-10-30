from fastapi import APIRouter, Request, Response, HTTPException
import os
import stripe

router = APIRouter()


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request) -> Response:
    """Minimal Stripe webhook handler with signature verification.

    Expects STRIPE_WEBHOOK_SECRET env var. Returns 204 on success.
    Currently a no-op after verification; extend with event handling as needed.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        # Not configured yet; reject so we don't accidentally process unverifiable requests.
        raise HTTPException(status_code=501, detail="Stripe webhook secret not configured")

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=webhook_secret,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    # No-op for now; in future, handle events like charge.succeeded, charge.refunded, etc.
    return Response(status_code=204)
