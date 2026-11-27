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
- Escrow runs in the payment provider's test mode only; no real money moves.
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
5. Escrow is released to the agent step by step as each step is confirmed:
   item bought, item shipped, item received. Cancelling refunds the buyer
   whatever has not been released.

Request states: open → quoted → accepted → paid (held) → bought → shipped →
received (fully released), or cancelled (unreleased funds refunded).

Non-goals for this version: browsing seller inventory, other routes, shipping
or logistics integration, ratings, real payments, open agent sign-up, and native phone apps.

## Technical choices

Not decided. Design selects the stack, payment provider, hosting, and proof
commands.

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

- **Release shares:** what share is released at each step (bought, shipped,
  received), and who confirms each step: the agent with proof such as a photo
  or receipt, or the buyer?
- **Exchange rate:** where does the CAD ↔ NGN rate come from, and is it fixed
  when the buyer accepts the quote?

## Links

None yet.
