#!/usr/bin/env python3
"""Heuristic scan of API routes / server actions for missing auth, rate limiting
and webhook verification. Results are LEADS to confirm by reading the code.

Usage: python scan_routes.py <project_root>
Output: SEVERITY | check | file:line | detail
"""
import os, re, sys

SKIP_DIRS = {"node_modules", ".git", ".next", "dist", "build", ".expo", ".vercel"}
CODE_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs")

AUTH_MARKERS = re.compile(
    r"getUser\(|getSession\(|auth\(\)|currentUser\(|getServerSession|requireAuth|withAuth|"
    r"verifyIdToken|getToken\(|clerkClient|authenticate|supabase\.auth|createServerClient|"
    r"createRouteHandlerClient|jwt\.verify|req\.user|session\b", re.I)
RATE_MARKERS = re.compile(
    r"ratelimit|rate[-_ ]?limit|Ratelimit|upstash|limiter|throttle|express-rate-limit|"
    r"slowDown|checkRateLimit|rl\.limit\(", re.I)
PAID_API = re.compile(
    r"openai|anthropic|api\.anthropic\.com|generativelanguage|replicate|resend|sendgrid|twilio|"
    r"nodemailer|\.messages\.create|chat\.completions|sendEmail|sendSms|elevenlabs", re.I)
PUBLIC_HINT = re.compile(r"(webhook|health|cron|public|og|callback|auth/)", re.I)
DB_BY_ID = re.compile(
    r"\.eq\(\s*['\"](?:id|[a-z_]*_id)['\"]\s*,\s*(?:params|body|searchParams|req\.|id\b|[a-zA-Z_.]*\.id\b)", re.I)
OWNER_CHECK = re.compile(r"user_id|userId|owner|auth\.uid|session\.user|user\.id", re.I)
SERVICE_CLIENT = re.compile(r"service_role|SERVICE_ROLE|supabaseAdmin|adminClient|createAdminClient", re.I)
STRIPE_HOOK = re.compile(r"stripe", re.I)
STRIPE_VERIFY = re.compile(r"constructEvent|constructEventAsync|webhooks\.construct", re.I)
CORS_STAR = re.compile(r"Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*['\"]|origin:\s*['\"]\*['\"]|cors\(\s*\)")
LIST_NO_LIMIT = re.compile(r"\.select\([^)]*\)\s*(?:\n\s*)?(?:;|$)", re.M)


def is_route(path, text):
    p = path.replace("\\", "/")
    if re.search(r"/app/.*/route\.(t|j)sx?$", p) or re.search(r"/pages/api/", p):
        return True
    if re.search(r"/(api|routes|server)/", p) and re.search(r"(router\.|app\.)(get|post|put|patch|delete)\(", text):
        return True
    if re.search(r"/supabase/functions/[^/]+/index\.ts$", p):
        return True
    return False


def is_server_action(text):
    return bool(re.search(r"""^['"]use server['"]""", text[:300], re.M))


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def main(root):
    findings = []
    seen = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if not fn.endswith(CODE_EXT):
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            try:
                text = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            route = is_route(p, text)
            action = is_server_action(text)
            if not (route or action):
                continue
            seen += 1
            kind = "route" if route else "server-action"
            public = bool(PUBLIC_HINT.search(rel))
            mutating = bool(re.search(r"export\s+(async\s+)?function\s+(POST|PUT|PATCH|DELETE)|\.(post|put|patch|delete)\(|insert\(|update\(|delete\(|upsert\(", text))
            has_auth = bool(AUTH_MARKERS.search(text))
            has_rate = bool(RATE_MARKERS.search(text))
            uses_paid = bool(PAID_API.search(text))
            uses_service = bool(SERVICE_CLIENT.search(text))

            if not has_auth and not public:
                sev = "HIGH" if (mutating or uses_service or uses_paid) else "MEDIUM"
                findings.append((sev, f"{kind}-no-auth-check", rel, 1,
                                 "No auth check found in this file. Confirm middleware or a wrapper protects it"))
            if uses_service and not has_auth:
                findings.append(("CRITICAL", f"{kind}-service-role-no-auth", rel, 1,
                                 "Uses an admin/service-role client with no visible auth check: bypasses RLS for anyone who calls it"))
            if uses_paid and not has_rate:
                findings.append(("HIGH", f"{kind}-paid-api-no-rate-limit", rel, 1,
                                 "Calls a paid API (LLM/email/SMS) with no rate limiting: one script can run up your bill"))
            if uses_paid and not has_auth:
                findings.append(("CRITICAL", f"{kind}-paid-api-unauthenticated", rel, 1,
                                 "Paid API reachable without login. Anyone can spend your credits"))
            if re.search(r"login|signin|sign-in|signup|register|reset|forgot|otp|verify", rel, re.I) and not has_rate:
                findings.append(("HIGH", f"{kind}-auth-endpoint-no-rate-limit", rel, 1,
                                 "Login/signup/reset/OTP endpoint with no rate limiting: brute force and email/SMS bombing"))
            if STRIPE_HOOK.search(text) and re.search(r"webhook", rel, re.I) and not STRIPE_VERIFY.search(text):
                findings.append(("CRITICAL", "stripe-webhook-unverified", rel, 1,
                                 "Webhook handler without constructEvent signature check: anyone can fake 'payment succeeded'"))
            for m in DB_BY_ID.finditer(text):
                window = text[max(0, m.start() - 600): m.end() + 400]
                if not OWNER_CHECK.search(window):
                    findings.append(("HIGH", f"{kind}-possible-idor", rel, line_of(text, m.start()),
                                     "Row fetched/changed by an id from the request with no visible ownership filter (IDOR). Confirm RLS or an explicit user_id check covers it"))
                    break
            for m in CORS_STAR.finditer(text):
                findings.append(("MEDIUM", "cors-wildcard", rel, line_of(text, m.start()),
                                 "Wildcard CORS. Fine for truly public data, risky with cookies or auth"))
                break
            if re.search(r"JSON\.parse\(|await\s+req\.json\(\)|request\.json\(\)", text) and \
               not re.search(r"\bz\.|zod|yup|joi|valibot|safeParse|ajv|superstruct|typebox", text, re.I) and mutating \
               and not re.search(r"webhook", rel, re.I):
                findings.append(("MEDIUM", f"{kind}-no-input-validation", rel, 1,
                                 "Request body used with no schema validation (zod/yup/etc.): malformed or malicious input reaches your logic"))

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    for sev, check, rel, ln, detail in sorted(set(findings), key=lambda f: (order[f[0]], f[2], f[3])):
        print(f"{sev} | {check} | {rel}:{ln} | {detail}")
    print(f"INFO | scan_routes | - | inspected {seen} route/action file(s). Heuristic only: auth in middleware "
          "or shared wrappers is not always detectable")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("usage: scan_routes.py <project_root>")
    main(os.path.abspath(sys.argv[1]))
