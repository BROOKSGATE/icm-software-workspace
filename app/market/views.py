from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import fx, orders, payments
from .forms import MessageForm, ProofForm, QuoteForm, RequestForm, SignupForm
from .models import Profile, Quote, SourcingRequest, StepRelease, is_agent


def _load(user, pk):
    """Return the request and the viewer's role, or 404 if this user may not see it.

    Agents see open requests without the buyer's details. Once a quote is
    accepted, only the buyer and the chosen agent can open the request.
    """
    req = get_object_or_404(SourcingRequest, pk=pk)
    chosen = req.accepted_quote
    if req.buyer_id == user.id:
        return req, "buyer", chosen
    if is_agent(user):
        if chosen and chosen.agent_id == user.id:
            return req, "agent", chosen
        if chosen is None and req.status in (SourcingRequest.OPEN, SourcingRequest.QUOTED):
            return req, "agent", chosen
    raise Http404


def signup(request):
    form = SignupForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        Profile.objects.create(user=user, role=Profile.BUYER, phone=form.cleaned_data["phone"])
        login(request, user)
        return redirect("home")
    return render(request, "market/signup.html", {"form": form})


@login_required
def home(request):
    if is_agent(request.user):
        open_requests = SourcingRequest.objects.filter(
            status__in=[SourcingRequest.OPEN, SourcingRequest.QUOTED]
        ).exclude(quotes__agent=request.user)
        my_quotes = Quote.objects.filter(agent=request.user).select_related("request")
        return render(request, "market/agent_home.html", {"open_requests": open_requests, "my_quotes": my_quotes})
    return render(request, "market/buyer_home.html", {"requests": request.user.requests.all()})


@login_required
def request_new(request):
    if is_agent(request.user):
        return HttpResponseForbidden("Agents cannot post requests.")
    form = RequestForm(request.POST or None)
    if form.is_valid():
        req = form.save(commit=False)
        req.buyer = request.user
        req.save()
        return redirect("request_detail", pk=req.pk)
    return render(request, "market/request_form.html", {"form": form})


@login_required
def request_detail(request, pk):
    req, role, chosen = _load(request.user, pk)
    context = {"req": req, "role": role, "chosen": chosen, "next_step": orders.next_step(req)}
    if role == "buyer" and chosen is None:
        try:
            rate = fx.ngn_per_cad()
            context["quotes"] = [(q, fx.ngn_to_cad(q.total_ngn, rate)) for q in req.quotes.all()]
        except Exception:
            context["quotes"] = [(q, None) for q in req.quotes.all()]
            messages.warning(request, "Exchange rate is unavailable right now; CAD prices are hidden.")
    if role == "agent" and chosen is None:
        mine = req.quotes.filter(agent=request.user).first()
        context["my_quote"] = mine
        context["quote_form"] = None if mine else QuoteForm()
    if chosen:
        context["message_form"] = MessageForm()
        context["proof_form"] = ProofForm()
        context["steps"] = req.steps.all()
        context["pending_step"] = req.steps.filter(confirmed_at__isnull=True).first()
    return render(request, "market/request_detail.html", context)


@login_required
@require_POST
def quote_create(request, pk):
    req, role, chosen = _load(request.user, pk)
    if role != "agent" or chosen or req.quotes.filter(agent=request.user).exists():
        return HttpResponseForbidden("You cannot quote on this request.")
    form = QuoteForm(request.POST)
    if form.is_valid():
        quote = form.save(commit=False)
        quote.request = req
        quote.agent = request.user
        quote.save()
        req.status = SourcingRequest.QUOTED
        req.save(update_fields=["status"])
        messages.success(request, "Quote sent.")
    else:
        messages.error(request, "Please check the quote amounts.")
    return redirect("request_detail", pk=pk)


@login_required
@require_POST
def quote_accept(request, pk, quote_id):
    req, role, _ = _load(request.user, pk)
    if role != "buyer":
        return HttpResponseForbidden()
    try:
        orders.accept_quote(quote_id, request.user)
        messages.success(request, "Quote accepted. You can now chat with your agent and pay into escrow.")
    except orders.OrderError as error:
        messages.error(request, str(error))
    return redirect("request_detail", pk=pk)


@login_required
@require_POST
def pay(request, pk):
    req, role, chosen = _load(request.user, pk)
    if role != "buyer" or req.status != SourcingRequest.ACCEPTED:
        return HttpResponseForbidden()
    success = request.build_absolute_uri(reverse("pay_done", args=[pk]))
    cancel = request.build_absolute_uri(reverse("request_detail", args=[pk]))
    return redirect(payments.create_checkout(req, success, cancel))


@login_required
def pay_done(request, pk):
    req, role, _ = _load(request.user, pk)
    if role != "buyer":
        return HttpResponseForbidden()
    try:
        orders.mark_paid(req, request.GET.get("session_id", ""))
        messages.success(request, "Payment received. It is held in escrow until you confirm each step.")
    except orders.OrderError as error:
        messages.error(request, str(error))
    return redirect("request_detail", pk=pk)


@login_required
def chat(request, pk):
    req, role, chosen = _load(request.user, pk)
    if not chosen:
        raise Http404
    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            form.instance.request = req
            form.instance.sender = request.user
            form.save()
        return redirect("request_detail", pk=pk)
    return render(request, "market/_chat.html", {"req": req})


@login_required
@require_POST
def proof_upload(request, pk):
    req, role, chosen = _load(request.user, pk)
    step = orders.next_step(req)
    if role != "agent" or not chosen or req.status not in (SourcingRequest.PAID, "bought", "shipped"):
        return HttpResponseForbidden()
    if req.steps.filter(step=step).exists():
        messages.error(request, "Proof for this step is already waiting for the buyer.")
        return redirect("request_detail", pk=pk)
    form = ProofForm(request.POST, request.FILES)
    if form.is_valid():
        form.instance.request = req
        form.instance.step = step
        form.save()
        messages.success(request, f"Proof for '{step}' sent to the buyer.")
    return redirect("request_detail", pk=pk)


@login_required
@require_POST
def step_confirm(request, pk, step):
    req, role, _ = _load(request.user, pk)
    if role != "buyer":
        return HttpResponseForbidden()
    try:
        release = orders.confirm_step(req.pk, step)
        messages.success(request, f"Released {release.amount_cad} CAD to your agent for '{step}'.")
    except (orders.OrderError, StepRelease.DoesNotExist) as error:
        messages.error(request, str(error) or "No proof has been uploaded for that step.")
    return redirect("request_detail", pk=pk)


@login_required
def proof_file(request, pk, step):
    req, _, chosen = _load(request.user, pk)
    if not chosen:
        raise Http404
    release = get_object_or_404(StepRelease, request=req, step=step)
    return FileResponse(release.proof.open("rb"))


@login_required
@require_POST
def cancel(request, pk):
    req, role, _ = _load(request.user, pk)
    if role != "buyer":
        return HttpResponseForbidden()
    try:
        refund = orders.cancel_request(req.pk)
        messages.success(request, f"Request cancelled. Refunded {refund} CAD.")
    except orders.OrderError as error:
        messages.error(request, str(error))
    return redirect("request_detail", pk=pk)
