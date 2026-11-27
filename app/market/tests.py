"""Proof for the SourceLink MVP acceptance criteria (projects/sourcelink-mvp/PROJECT.md).

Stripe and the exchange-rate site are replaced with unittest.mock, so these
tests run offline. `manage.py check_stripe` makes the one real Stripe call.
"""

import shutil
import tempfile
from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Profile, Quote, SourcingRequest

RATE = Decimal("1000")  # NGN per CAD in these tests

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
@mock.patch("market.fx.ngn_per_cad", return_value=RATE)
class MarketplaceFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.buyer = self._user("ada", Profile.BUYER, phone="+1 905 555 0100")
        self.agent = self._user("tunde", Profile.AGENT, account="acct_tunde")
        self.other_agent = self._user("bisi", Profile.AGENT, account="acct_bisi")

    def _user(self, name, role, phone="", account=""):
        user = User.objects.create_user(name, f"{name}@example.com", "pass-12345")
        Profile.objects.create(user=user, role=role, phone=phone, stripe_account_id=account)
        return user

    def _as(self, user):
        self.client.force_login(user)
        return self.client

    def _post_request(self):
        self._as(self.buyer).post(
            reverse("request_new"),
            {"item": "Aso-oke fabric", "quantity": 3, "budget_cad": "300", "delivery_city": "Oshawa",
             "deadline": date(2027, 1, 15)},
        )
        return SourcingRequest.objects.get()

    def _quote(self, req, agent, total_ngn):
        self._as(agent).post(
            reverse("quote_create", args=[req.pk]),
            {"item_price_ngn": total_ngn - 20000, "sourcing_fee_ngn": "15000", "shipping_ngn": "5000",
             "timeline": "10 days"},
        )
        return Quote.objects.get(request=req, agent=agent)

    def _paid_order(self):
        req = self._post_request()
        quote = self._quote(req, self.agent, 200000)
        self._as(self.buyer).post(reverse("quote_accept", args=[req.pk, quote.pk]))
        return self._paid_order_from(req)

    def _upload_and_confirm(self, req, step):
        proof = SimpleUploadedFile("receipt.jpg", b"fake image", content_type="image/jpeg")
        self._as(self.agent).post(reverse("proof_upload", args=[req.pk]), {"proof": proof})
        return self._as(self.buyer).post(reverse("step_confirm", args=[req.pk, step]))

    def test_full_flow_from_request_to_staged_release(self, _rate):
        req = self._post_request()
        # Open requests appear to signed-in agents.
        self.assertContains(self._as(self.agent).get(reverse("home")), "Aso-oke fabric")

        mine = self._quote(req, self.agent, 200000)
        other = self._quote(req, self.other_agent, 250000)
        # The buyer sees the NGN quote in CAD.
        self.assertContains(self._as(self.buyer).get(reverse("request_detail", args=[req.pk])), "200.00 CAD")

        self._as(self.buyer).post(reverse("quote_accept", args=[req.pk, mine.pk]))
        mine.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual((mine.status, other.status), (Quote.ACCEPTED, Quote.CLOSED))
        self.assertEqual((mine.rate_ngn_per_cad, mine.total_cad), (RATE, Decimal("200.00")))

        req = self._paid_order_from(req)
        self.assertEqual((req.status, req.paid_cad), (SourcingRequest.PAID, Decimal("200.00")))

        with mock.patch("market.payments.transfer_to_agent", return_value="tr_x") as transfer:
            for step in ["bought", "shipped", "received"]:
                self._upload_and_confirm(req, step)
        amounts = [c.args[2] for c in transfer.call_args_list]
        self.assertEqual(amounts, [Decimal("80.00"), Decimal("60.00"), Decimal("60.00")])
        self.assertEqual({c.args[3] for c in transfer.call_args_list}, {"acct_tunde"})
        req.refresh_from_db()
        self.assertEqual((req.status, req.released_cad()), ("received", Decimal("200.00")))

    def _paid_order_from(self, req):
        paid = {"request_id": str(req.pk), "payment_intent": "pi_1", "charge": "ch_1", "amount_cad": Decimal("200.00")}
        with mock.patch("market.payments.confirm_checkout", return_value=paid):
            self._as(self.buyer).get(reverse("pay_done", args=[req.pk]), {"session_id": "cs_1"})
        req.refresh_from_db()
        return req

    def test_only_invited_agents_can_quote(self, _rate):
        req = self._post_request()
        response = self._as(self.buyer).post(
            reverse("quote_create", args=[req.pk]),
            {"item_price_ngn": "1", "sourcing_fee_ngn": "1", "shipping_ngn": "1", "timeline": "1 day"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Quote.objects.exists())

    def test_buyer_details_and_chat_are_private_to_the_chosen_agent(self, _rate):
        req = self._post_request()
        detail = reverse("request_detail", args=[req.pk])
        self.assertNotContains(self._as(self.agent).get(detail), "ada@example.com")

        quote = self._quote(req, self.agent, 200000)
        self._as(self.buyer).post(reverse("quote_accept", args=[req.pk, quote.pk]))
        self._as(self.buyer).post(reverse("chat", args=[req.pk]), {"body": "My gate code is 1234"})

        self.assertContains(self._as(self.agent).get(detail), "ada@example.com")
        self.assertContains(self._as(self.agent).get(reverse("chat", args=[req.pk])), "gate code")
        self.assertEqual(self._as(self.other_agent).get(detail).status_code, 404)
        self.assertEqual(self._as(self.other_agent).get(reverse("chat", args=[req.pk])).status_code, 404)

    def test_a_step_is_never_paid_twice(self, _rate):
        req = self._paid_order()
        with mock.patch("market.payments.transfer_to_agent", return_value="tr_x") as transfer:
            self._upload_and_confirm(req, "bought")
            self._as(self.buyer).post(reverse("step_confirm", args=[req.pk, "bought"]))
        self.assertEqual(transfer.call_count, 1)

    def test_cancelling_refunds_only_what_was_not_released(self, _rate):
        req = self._paid_order()
        with mock.patch("market.payments.transfer_to_agent", return_value="tr_x"):
            self._upload_and_confirm(req, "bought")
        with mock.patch("market.payments.refund", return_value="re_x") as refund:
            self._as(self.buyer).post(reverse("cancel", args=[req.pk]))
        refund.assert_called_once()
        self.assertEqual(refund.call_args.args[1], Decimal("120.00"))
        req.refresh_from_db()
        self.assertEqual((req.status, req.refunded_cad), (SourcingRequest.CANCELLED, Decimal("120.00")))

    def test_live_stripe_keys_are_refused(self, _rate):
        from . import payments

        with override_settings(STRIPE_SECRET_KEY="sk_live_abc"):
            with self.assertRaises(RuntimeError):
                payments.check_account()
