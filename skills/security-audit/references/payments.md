# Payments and webhooks (Stripe focus)

## Webhooks (Critical)
- The webhook handler must verify the signature with `stripe.webhooks.constructEvent(rawBody, sig, STRIPE_WEBHOOK_SECRET)`. Without it, anyone can POST a fake `checkout.session.completed` and get a free upgrade.
- Verification needs the **raw body**. In Next.js route handlers use `await req.text()`; parsing JSON first breaks the signature, and AI "fixes" this by removing verification. Check it wasn't removed.
- Make handlers **idempotent**: store processed `event.id` and skip repeats (Stripe retries).
- Handle at least: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted`. Missing the last two means cancelled users keep access.
- Return 2xx quickly; do heavy work async.

## Checkout creation
- Look up price server-side from a price id you control. Never trust `amount` or `price` from the client.
- Attach the verified user id (`client_reference_id` or metadata) server-side.
- Success page is not proof of payment. Grant access from the webhook or by re-fetching the session server-side.

## Entitlements
- Store plan/subscription state in your DB, updated only by the webhook (service role or server). Users must not have an update policy on those columns.
- Check entitlement server-side on every gated action.

## Keys
- `sk_live_` / `rk_live_` server-only. Publishable key `pk_` is fine in the client.
- Use restricted keys with least privilege where possible.
- Test and live keys and webhook secrets kept separate per environment.

## Other providers
Razorpay, Paddle, Lemon Squeezy and others follow the same rules: verify the signature header with the provider's secret, idempotency, server-side price, entitlement from webhook only.
