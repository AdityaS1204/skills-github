# Rate limiting and abuse

AI tools almost never add rate limiting. The cost shows up as a surprise bill or a flooded inbox, not a hack headline, so rank by money at risk.

## Priority order
1. **Endpoints that call paid APIs** (LLMs, image generation, email, SMS, OTP, maps, speech): Critical if unauthenticated, High if authenticated but unlimited. One looping script drains credits.
2. **Auth endpoints**: login, signup, password reset, magic link, OTP/verify. Limit per IP and per account/email to stop brute force and email/SMS bombing.
3. **Write-heavy or expensive endpoints**: file upload, search, export, report generation, anything with heavy DB work.
4. **Everything else**: a generous global limit is enough.

## Per-user quotas, not just per-IP
IP limits are easy to evade. For paid features also cap per user per day (credits table, usage counter) and enforce it **server-side before** calling the provider.

## Cheap implementations by stack
- **Next.js / serverless (Vercel)**: `@upstash/ratelimit` + Upstash Redis (free tier) in the route or middleware. In-memory counters don't work on serverless since each invocation may be a fresh instance.
- **Express/Fastify on a long-running server**: `express-rate-limit` / `@fastify/rate-limit` (use a Redis store if more than one instance).
- **Supabase**: Edge Functions + Upstash, or a Postgres counter table checked inside the function. Enable CAPTCHA (Turnstile/hCaptcha) on Supabase Auth for signup and login. Auth has built-in per-hour limits for email/SMS you should review in the dashboard.
- **Firebase**: App Check, plus a counter in Firestore or Cloud Functions for paid operations.
- **Edge/CDN**: Cloudflare rate limiting rules or Vercel Firewall for blanket protection.

Return `429` with a `Retry-After` header.

## Other abuse controls
- Max request body size and upload size/type limits.
- Max tokens and input length on LLM calls (set `max_tokens`, cap prompt size) so one request can't cost dollars.
- Provider-side hard spend limits (OpenAI/Anthropic usage limits, Twilio, AWS budgets) as the last safety net. Tell the user to set these in the provider dashboard.
- Signup abuse: disposable-email blocking or CAPTCHA if free credits are given on signup.
- Don't let the user choose the model or system prompt on a paid LLM endpoint without validation.
