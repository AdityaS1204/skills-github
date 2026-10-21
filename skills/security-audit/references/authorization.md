# Authorization: can user A touch user B's data?

Authentication asks "who are you?". Authorization asks "are you allowed to do this to this row?". AI-built apps get the first right and skip the second. This is the single most common serious bug in vibe-coded apps (IDOR: insecure direct object reference).

## What to look for
For every route, server action, RPC or edge function that takes an id (`/api/orders/[id]`, `?projectId=`, `body.noteId`):
1. Is the id used to fetch or modify a row?
2. Does the query also filter by the verified user (`.eq('user_id', user.id)`), or does RLS/security rules enforce it?
3. If using a service-role / admin client: RLS is bypassed, so the code **must** filter or check ownership itself.

Red flags:
- `supabase.from('x').select().eq('id', params.id).single()` using an admin client, with no `user_id` filter.
- `update ... where id = $1` with no `and user_id = $2`.
- Prisma/Drizzle `findUnique({ where: { id } })` followed by returning it with no owner comparison.
- Fetching "current user's data" by a `userId` taken from the request instead of the session.
- Multi-tenant apps: missing `org_id`/`team_id` membership check.
- Sequential integer ids make this trivially enumerable. UUIDs help but are not a fix.

## Mass assignment
- `update(req.body)` or `insert({...body})` lets users set columns like `role`, `is_admin`, `plan`, `credits`, `user_id`, `price`. Whitelist fields explicitly.

## Business logic the client shouldn't decide
- Prices, discounts, credits and plan limits computed client-side and trusted by the server.
- Checkout that takes `amount` from the request rather than looking up the price server-side.
- Free-tier limits enforced only in the UI.

## Fix pattern
Derive identity from the verified token, scope every query by it, and prefer RLS as the backstop so a forgotten filter fails closed.
