from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Message, Quote, SourcingRequest, StepRelease


class SignupForm(UserCreationForm):
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email"]


class RequestForm(forms.ModelForm):
    class Meta:
        model = SourcingRequest
        fields = ["item", "quantity", "budget_cad", "delivery_city", "deadline"]
        labels = {"budget_cad": "Budget (CAD)"}
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"})}


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ["item_price_ngn", "sourcing_fee_ngn", "shipping_ngn", "timeline", "note"]
        labels = {
            "item_price_ngn": "Item price (NGN)",
            "sourcing_fee_ngn": "Your sourcing fee (NGN)",
            "shipping_ngn": "Shipping estimate (NGN)",
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["body"]
        labels = {"body": ""}
        widgets = {"body": forms.Textarea(attrs={"rows": 2, "placeholder": "Write a message"})}


class ProofForm(forms.ModelForm):
    class Meta:
        model = StepRelease
        fields = ["proof", "note"]
        labels = {"proof": "Photo or receipt"}
