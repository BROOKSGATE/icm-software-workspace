from decimal import Decimal

from django.conf import settings
from django.db import models

STEPS = ["bought", "shipped", "received"]
STEP_SHARES = {"bought": Decimal("0.40"), "shipped": Decimal("0.30"), "received": Decimal("0.30")}


class Profile(models.Model):
    BUYER = "buyer"
    AGENT = "agent"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[(BUYER, "Buyer"), (AGENT, "Agent")], default=BUYER)
    phone = models.CharField(max_length=30, blank=True)
    stripe_account_id = models.CharField(
        max_length=40, blank=True, help_text="Agent's Stripe test connected account (acct_...)."
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"


def is_agent(user):
    return hasattr(user, "profile") and user.profile.role == Profile.AGENT


class SourcingRequest(models.Model):
    OPEN = "open"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    PAID = "paid"
    CANCELLED = "cancelled"
    STATUSES = [
        (OPEN, "Open"),
        (QUOTED, "Quoted"),
        (ACCEPTED, "Accepted"),
        (PAID, "Paid (held)"),
        ("bought", "Bought"),
        ("shipped", "Shipped"),
        ("received", "Received"),
        (CANCELLED, "Cancelled"),
    ]

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requests")
    item = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    budget_cad = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_city = models.CharField(max_length=100, help_text="City in Canada")
    deadline = models.DateField()
    status = models.CharField(max_length=10, choices=STATUSES, default=OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    stripe_payment_intent = models.CharField(max_length=60, blank=True)
    stripe_charge = models.CharField(max_length=60, blank=True)
    paid_cad = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refunded_cad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.item}"

    @property
    def accepted_quote(self):
        return self.quotes.filter(status=Quote.ACCEPTED).first()

    def released_cad(self):
        total = self.steps.filter(confirmed_at__isnull=False).aggregate(s=models.Sum("amount_cad"))["s"]
        return total or Decimal("0")


class Quote(models.Model):
    SENT = "sent"
    ACCEPTED = "accepted"
    CLOSED = "closed"

    request = models.ForeignKey(SourcingRequest, on_delete=models.CASCADE, related_name="quotes")
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="quotes")
    item_price_ngn = models.DecimalField(max_digits=14, decimal_places=2)
    sourcing_fee_ngn = models.DecimalField(max_digits=14, decimal_places=2)
    shipping_ngn = models.DecimalField(max_digits=14, decimal_places=2)
    timeline = models.CharField(max_length=100, help_text="For example: 10 days")
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=[(SENT, "Sent"), (ACCEPTED, "Accepted"), (CLOSED, "Closed")], default=SENT
    )
    # Fixed when the buyer accepts the quote.
    rate_ngn_per_cad = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    total_cad = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["request", "agent"], name="one_quote_per_agent")]

    @property
    def total_ngn(self):
        return self.item_price_ngn + self.sourcing_fee_ngn + self.shipping_ngn


class Message(models.Model):
    request = models.ForeignKey(SourcingRequest, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class StepRelease(models.Model):
    request = models.ForeignKey(SourcingRequest, on_delete=models.CASCADE, related_name="steps")
    step = models.CharField(max_length=10, choices=[(s, s.title()) for s in STEPS])
    proof = models.FileField(upload_to="proofs/")
    note = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    amount_cad = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stripe_transfer = models.CharField(max_length=60, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["request", "step"], name="one_release_per_step")]
