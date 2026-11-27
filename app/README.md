# Application code

SourceLink's Django app lives here (stack chosen in
[`projects/sourcelink-mvp`](../projects/sourcelink-mvp/PROJECT.md#technical-choices)).

| Path | Owns |
|---|---|
| `sourcelink/` | Django settings and root URLs |
| `market/models.py` | Requests, quotes, chat messages, release steps |
| `market/orders.py` | Order rules: accept, pay, staged release, cancel |
| `market/payments.py` | Every Stripe call (test keys only) |
| `market/fx.py` | CAD ↔ NGN rate from ExchangeRate-API |
| `market/tests.py` | Proof for the brief's acceptance criteria |

## Run it locally

From the repository root, with Python 3.10+:

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install "django>=5.2,<6" stripe requests
cd app
cp .env.example .env          # then put your Stripe test secret key in .env
python manage.py migrate
python manage.py createsuperuser
python manage.py check_stripe # one real call to confirm the test key
python manage.py runserver
```

Open http://127.0.0.1:8000/admin/ to invite an agent: add a user, set the
Profile role to Agent, and paste their Stripe test connected account id
(`acct_...`). Buyers sign up at http://127.0.0.1:8000/signup/.
