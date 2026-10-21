---
name: vibe-security-audit
description: Pre-launch security and performance audit for AI-built ("vibe coded") web and mobile apps. Checks the basics AI coding tools skip unless told - Supabase/Firebase row level security and rules, leaked API keys and service-role keys, auth token handling, missing authorization (IDOR), rate limiting on login and paid-API endpoints, Stripe webhook verification, and common performance problems like N+1 queries, missing indexes and unpaginated queries. Use this skill whenever the user says they are about to launch, deploy or ship, asks "is my app secure", "is my Supabase safe", "check my RLS", "security review", "audit my app", "production ready", or pastes a Next.js/React/Expo/Supabase/Firebase project and wants it hardened - even if they never say the word "security".
---

# Vibe Security Audit

AI coding tools build features that work, then stop. They rarely turn on row level security, add rate limits, verify webhooks, or check that user A can't read user B's rows, because nobody asked. This skill is the "did anyone ask?" pass: it inspects the actual codebase, reports what it finds with file paths and line numbers, and offers fixes the user approves before anything changes.

The audience is usually a solo builder who is not a security engineer. Write findings in plain language, say why each one matters in one sentence, and give the exact fix. Skip jargon unless it's defined the first time.

## Workflow

### 1. Locate the project and detect the stack

Find the project root (look for `package.json`, `supabase/`, `firebase.json`, `app.json`). Identify:

- Framework: Next.js (app or pages router), Vite/React, Expo/React Native, Express/Fastify, other
- Backend: Supabase, Firebase, custom API, serverless functions
- Auth: Supabase Auth, Firebase Auth, NextAuth/Auth.js, Clerk, custom JWT
- Payments: Stripe, Razorpay, other
- Hosting hints: `vercel.json`, `netlify.toml`, Dockerfile

State the detected stack in one line before continuing. If something is ambiguous, say what you assumed instead of stopping to ask.

If the user only pasted code or described the app (no filesystem access to the project), skip the scripts and review the pasted code against the reference checklists by hand, and say clearly that coverage is partial.

### 2. Run the deterministic scanners

These catch the things a regex or parser can catch reliably. Run the ones that apply, pointing at the project root:

```bash
python scripts/scan_secrets.py <project_root>
python scripts/check_rls.py <project_root>        # Supabase/Postgres projects
python scripts/scan_routes.py <project_root>      # Next.js / Express style API routes
```

Each prints findings as `SEVERITY | check | file:line | detail`. Treat scanner output as leads, not verdicts: confirm each one by reading the surrounding code before reporting it. A scanner hit you did not verify should be labelled "needs confirmation" in the report.

### 3. Do the judgment checks

Scripts can't judge intent. Read the relevant reference file for each area that applies and work through it against the real code:

| Area | Read | When |
|---|---|---|
| Supabase | `references/supabase.md` | Any Supabase usage |
| Firebase | `references/firebase.md` | Firestore, Realtime DB, Storage, Cloud Functions |
| Auth and tokens | `references/auth.md` | Always |
| Authorization (IDOR) | `references/authorization.md` | Any API route, server action or RPC that reads/writes user data |
| Rate limiting and abuse | `references/rate-limiting.md` | Always; critical if any paid API (LLM, email, SMS) is called |
| Webhooks and payments | `references/payments.md` | Stripe or other payment provider |
| Performance | `references/performance.md` | Always, lower priority than security |

Only open the files for the areas that apply, so context stays small.

### 4. Report

Use `assets/report-template.md` as the structure. Rules for the report:

- **Rank by severity**: Critical (data exposed or money at risk right now), High, Medium, Low. Lead with Critical.
- **Every finding has**: what is wrong, where (file:line), why it matters in one sentence, and the specific fix.
- **Include a "Not checked" section.** List what this audit did not cover (for example: dependencies with known CVEs, infrastructure config, anything not in the repo like dashboard-only Supabase settings). This matters because a clean report that silently skips areas gives false confidence, which is worse than no audit.
- **Include a "Verify in the dashboard" section** for things the repo can't prove: RLS actually enabled in the live database, auth redirect URLs, email confirmation, API key restrictions, spend limits.
- Do not say "your app is secure." Say "no issues found in the areas checked."
- Keep the top of the report to 5 to 8 "fix these first" items. A 40-item dump gets ignored.

### 5. Offer fixes, gated

After the report, offer to fix Critical and High items. Show diffs or SQL and get approval before applying. Auto-generated RLS policies in particular can lock every user out or quietly open everything up, so:

- Propose policies per table with a one-line explanation of who can do what.
- Tell the user how to test them (log in as two different users, try to read the other's row).
- Never run SQL against a live database yourself. Give the user the migration to apply.

## Ground rules

- Never print full secret values in the report. Show the first 4 and last 2 characters.
- If a live secret is committed or exposed, say it must be **rotated**, not just removed. Deleting it from the repo does not unleak it.
- Don't invent findings to look thorough. If a check passes, say it passed in a short "Looks good" list.
- Match the fix to the user's stack. Don't suggest Redis-backed rate limiting to someone on a free Vercel hobby plan if a simple Upstash or in-DB approach fits.
- This is a baseline hygiene pass, not a penetration test. Say so once in the report footer.
