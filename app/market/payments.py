"""Every Stripe call lives here. Test mode only: live keys are refused."""

from decimal import Decimal

import stripe
from django.conf import settings


def _stripe():
    key = settings.STRIPE_SECRET_KEY
    if not key.startswith("sk_test_"):
        raise RuntimeError("Set STRIPE_SECRET_KEY to a Stripe test key (sk_test_...) in app/.env.")
    stripe.api_key = key
    return stripe


def cents(amount_cad):
    return int((amount_cad * 100).to_integral_value())


def create_checkout(req, success_url, cancel_url):
    """Start Stripe Checkout for the accepted quote's CAD total; return the page to send the buyer to."""
    session = _stripe().checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "cad",
                    "unit_amount": cents(req.accepted_quote.total_cad),
                    "product_data": {"name": f"SourceLink request #{req.pk}: {req.item}"},
                },
                "quantity": 1,
            }
        ],
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"request_id": str(req.pk)},
        payment_intent_data={"transfer_group": f"request-{req.pk}"},
    )
    return session.url


def confirm_checkout(session_id):
    """Return the paid checkout's request id, payment intent, charge and CAD amount, or None if unpaid."""
    session = _stripe().checkout.Session.retrieve(session_id, expand=["payment_intent"])
    if session.payment_status != "paid":
        return None
    intent = session.payment_intent
    return {
        "request_id": session.metadata["request_id"],
        "payment_intent": intent.id,
        "charge": intent.latest_charge,
        "amount_cad": Decimal(session.amount_total) / 100,
    }


def transfer_to_agent(req, step, amount_cad, account_id):
    """Send one step's share from the held payment to the agent. The key makes a retry safe."""
    transfer = _stripe().Transfer.create(
        amount=cents(amount_cad),
        currency="cad",
        destination=account_id,
        source_transaction=req.stripe_charge,
        transfer_group=f"request-{req.pk}",
        idempotency_key=f"request-{req.pk}-{step}",
    )
    return transfer.id


def refund(req, amount_cad):
    return _stripe().Refund.create(payment_intent=req.stripe_payment_intent, amount=cents(amount_cad)).id


def check_account():
    """One real call to confirm the key works and is in test mode."""
    balance = _stripe().Balance.retrieve()
    return balance.livemode, [f"{b.amount / 100:.2f} {b.currency.upper()}" for b in balance.available]
