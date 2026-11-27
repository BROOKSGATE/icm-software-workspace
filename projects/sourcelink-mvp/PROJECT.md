---
type: project
id: sourcelink-mvp
title: Buyer request, agent quote, and test-mode escrow on the Nigeria ↔ Canada route
---

# Feature brief

## Intent

A buyer in Canada who needs goods from Nigeria today has to travel or rely on
informal contacts. SourceLink's first version lets the buyer get goods sourced
by a local agent in Nigeria, with payment held in escrow until it is released.

Fixed constraints:

- One route only: buyers in Canada, agents in Nigeria.
- Mobile-friendly web app.
- Prototype quality bar (see [README](../../README.md#this-instance)).
- Escrow runs in Flutterwave's test mode only; no real money moves.
- [Privacy and payment principles](../../_shared/principles/product-principles.md)
  and [UI rules](../../_shared/ux/ui-ux-rules.md) apply.

## Product behavior

Workflow:

1. A buyer signs in and posts a sourcing request: item description, quantity,
   budget, delivery city in Canada, and deadline.
2. Agents join only by Alexander's invitation. Signed-in agents see open
   requests and send a quote in NGN: item price, sourcing fee, shipping
   estimate, and timeline. The buyer sees each quote in CAD.
3. The buyer compares quotes and accepts one. The other quotes close, and a
   chat opens between the buyer and the chosen agent only.
4. The buyer pays the accepted total into escrow through the provider's hosted
   checkout, using a test card.
5. Escrow is released to the agent step by step: 40% when the item is bought,
   30% when shipped, 30% when received. For each step the agent uploads proof
   (a photo or receipt) and the buyer confirms it. Cancelling refunds the buyer
   whatever has not been released.

Request states: open → quoted → accepted → paid (held) → bought → shipped →
received (fully released), or cancelled (unreleased funds refunded).

Non-goals for this version: browsing seller inventory, other routes, shipping
or logistics integration, ratings, real payments, open agent sign-up, and native phone apps.

## Technical choices

Accepted in chat 2026-11-26.

- **Stack:** Python and Django, server-rendered mobile-friendly pages. Django
  admin is where Alexander invites agents. Chat is a page that checks for new
  messages every few seconds; no real-time server.
- **Payments:** Flutterwave test mode. The buyer pays the accepted total
  through Flutterwave Checkout into SourceLink's Flutterwave balance; that
  held balance is the escrow. Each confirmed step sends its share to the
  agent's NGN bank account with a Flutterwave transfer. A step is recorded
  before its transfer is sent, so it can never be paid twice.
- **Exchange rate:** Flutterwave's transfer-rates endpoint gives the live
  CAD ↔ NGN estimate (it updates a few times a day). The rate is fixed on the
  quote when the buyer accepts it.
- **Secrets:** Flutterwave keys live in environment variables, never in the
  repository.
- **Delivery:** one PR for the first working version, split only if it grows
  too large to review.

Uncertainty to resolve first in Build:

- Flutterwave's documentation does not confirm collecting CAD by card. Build
  checks it in the sandbox first. If CAD is not supported, the buyer pays in
  USD and sees the CAD estimate (a product change returned to Alexander).
- Flutterwave's own escrow feature is documented only for an old API version,
  so the design does not depend on it.
- Holding buyers' money on the platform is fine in test mode, but real money
  needs a compliance review before any release.

## Acceptance and proof

- From a phone browser, a buyer can post a request, and it appears to
  signed-in agents.
- Only invited agents can quote. An agent quotes in NGN, and the buyer sees the
  quote in CAD.
- The buyer accepts a quote, the other quotes close, and only the buyer and the
  chosen agent can read their chat.
- The buyer pays the accepted total with a provider test card, and the request
  shows the funds as held.
- Each confirmed step releases its share to the agent in test mode; cancelling
  refunds only what has not been released.
- An agent does not see the buyer's contact details until the buyer accepts
  that agent's quote.
- SourceLink stores no card or bank account numbers; payment details stay with
  the provider.

Design names the smallest set of tests that prove these.

## Open questions

None.

## Links

None yet.
