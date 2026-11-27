"""SourceLink order rules: accepting quotes, payment, step-by-step release, and cancellation."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from . import fx, payments
from .models import STEP_SHARES, STEPS, Quote, SourcingRequest


class OrderError(Exception):
    pass


def accept_quote(quote_id, buyer):
    """Accept one quote, close the others, and fix the exchange rate on it."""
    with transaction.atomic():
        quote = Quote.objects.select_for_update().select_related("request").get(pk=quote_id, request__buyer=buyer)
        req = quote.request
        if req.status not in (SourcingRequest.OPEN, SourcingRequest.QUOTED):
            raise OrderError("A quote has already been accepted for this request.")
        rate = fx.ngn_per_cad()
        quote.rate_ngn_per_cad = rate
        quote.total_cad = fx.ngn_to_cad(quote.total_ngn, rate)
        quote.status = Quote.ACCEPTED
        quote.save()
        req.quotes.exclude(pk=quote.pk).update(status=Quote.CLOSED)
        req.status = SourcingRequest.ACCEPTED
        req.save(update_fields=["status"])
    return quote


def mark_paid(req, session_id):
    """Record a paid Stripe Checkout; the money now waits in SourceLink's balance (the escrow)."""
    if req.status != SourcingRequest.ACCEPTED:
        return
    paid = payments.confirm_checkout(session_id)
    if paid is None or paid["request_id"] != str(req.pk):
        raise OrderError("Payment was not completed.")
    if paid["amount_cad"] != req.accepted_quote.total_cad:
        raise OrderError("The amount paid does not match the accepted quote.")
    req.stripe_payment_intent = paid["payment_intent"]
    req.stripe_charge = paid["charge"]
    req.paid_cad = paid["amount_cad"]
    req.status = SourcingRequest.PAID
    req.save()


def next_step(req):
    done = set(req.steps.filter(confirmed_at__isnull=False).values_list("step", flat=True))
    return next((step for step in STEPS if step not in done), None)


def confirm_step(req_id, step):
    """Buyer confirms a step: record it and send its share. A step can never be paid twice."""
    with transaction.atomic():
        req = SourcingRequest.objects.select_for_update().get(pk=req_id)
        if req.status not in (SourcingRequest.PAID, "bought", "shipped"):
            raise OrderError("Nothing can be released on this request now.")
        if step != next_step(req):
            raise OrderError("Steps are released in order: bought, shipped, received.")
        release = req.steps.get(step=step)
        if step == "received":
            amount = req.paid_cad - req.released_cad()  # the last step takes any rounding remainder
        else:
            amount = (req.paid_cad * STEP_SHARES[step]).quantize(Decimal("0.01"))
        release.amount_cad = amount
        release.confirmed_at = timezone.now()
        account = req.accepted_quote.agent.profile.stripe_account_id
        release.stripe_transfer = payments.transfer_to_agent(req, step, amount, account)
        release.save()
        req.status = step
        req.save(update_fields=["status"])
    return release


def cancel_request(req_id):
    """Cancel and refund whatever has not been released to the agent."""
    with transaction.atomic():
        req = SourcingRequest.objects.select_for_update().get(pk=req_id)
        if req.status in ("received", SourcingRequest.CANCELLED):
            raise OrderError("This request can no longer be cancelled.")
        refund = Decimal("0")
        if req.paid_cad:
            refund = req.paid_cad - req.released_cad()
            if refund > 0:
                payments.refund(req, refund)
        req.refunded_cad = refund
        req.status = SourcingRequest.CANCELLED
        req.save()
        req.quotes.filter(status=Quote.SENT).update(status=Quote.CLOSED)
    return refund
