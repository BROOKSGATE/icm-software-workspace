"""CAD ↔ NGN rate from ExchangeRate-API's open endpoint (updated daily; attribution required)."""

from decimal import Decimal

import requests
from django.core.cache import cache

RATE_URL = "https://open.er-api.com/v6/latest/CAD"


def ngn_per_cad():
    rate = cache.get("ngn_per_cad")
    if rate is None:
        response = requests.get(RATE_URL, timeout=10)
        response.raise_for_status()
        rate = Decimal(str(response.json()["rates"]["NGN"]))
        cache.set("ngn_per_cad", rate, 60 * 60)
    return rate


def ngn_to_cad(amount_ngn, rate):
    return (amount_ngn / rate).quantize(Decimal("0.01"))
