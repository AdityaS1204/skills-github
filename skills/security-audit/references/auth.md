# Auth and token handling

Check what the code actually does. AI-generated auth usually works on the happy path and is loose everywhere else.

## Verify on the server, always (Critical)
- Hiding a button or redirecting in client code is not protection. Every protected API route, server action and RPC must verify identity on the server.
- Supabase: use `supabase.auth.getUser()` on the server. `getSession()` reads the cookie without re-validating and must not be trusted for authorization decisions in server code.
- Firebase: `verifyIdToken` in the backend. Clerk/NextAuth: use their server helpers.
- Next.js middleware alone is not enough as the only gate (it has had bypasses and doesn't cover every path). Check inside the handler too.
- Never accept `userId`, `role`, `isAdmin` or `plan` from the request body or query string as the source of truth. Derive from the verified token.

## Token storage
- Web: prefer httpOnly, Secure, SameSite=Lax/Strict cookies for session tokens. Tokens in `localStorage` are readable by any XSS. Flag `localStorage.setItem('token'` and similar.
- React Native/Expo: use `expo-secure-store` / Keychain / Keystore, not AsyncStorage, for tokens.
- Don't put tokens or keys in URLs (they land in logs and referrers).
- Don't log tokens, passwords or full request bodies.

## JWT specifics (custom auth)
- Verify signature with a strong secret from env, pin the algorithm (reject `none`), check `exp`, `iss`, `aud`.
- Hardcoded or short secrets like `"secret"`, `"supersecret"` are Critical.
- Access tokens short-lived (about 15 min to 1 h), refresh tokens rotated and revocable.
- Password hashing: bcrypt/argon2/scrypt only. MD5/SHA-* of passwords is Critical.

## Flows people forget
- Password reset: tokens single-use, expire quickly, don't reveal whether an email exists.
- Email confirmation required before access to anything sensitive.
- OAuth redirect URLs: exact allow-list, no wildcards.
- Logout actually invalidates the session server-side where possible.
- Admin routes: check a server-side role, not just "logged in".
- Session cookies: `Secure`, `HttpOnly`, `SameSite` set; CSRF protection on cookie-authenticated mutating routes (SameSite helps; check state-changing GETs).

## Headers worth a quick check
`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`, `frame-ancestors`/`X-Frame-Options`. Low severity for most side projects, but cheap to add (Next.js `headers()` in `next.config`).
