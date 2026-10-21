# Performance checks AI tools skip

Lower severity than security, but these cause the "it was fast with 10 rows" outage. Report as Medium/Low unless something is clearly going to break at modest scale.

## Database
- **Missing indexes**: columns used in `.eq()`, `where`, `order by`, joins, and every foreign key and every column referenced in RLS policies (`user_id`!). RLS on an unindexed `user_id` column makes every query a full table scan. Suggest `create index on public.t (user_id);`.
- **N+1 queries**: a loop that awaits a query per item, or a component per row that fetches its own data. Fix with a join / `in (...)` / Supabase embedded select (`select('*, comments(*)')`).
- **`select *`** on wide tables or tables with big text/jsonb columns; select the columns you need.
- **Unbounded lists**: queries with no `.limit()` / `.range()` / pagination, `getDocs(collection)` with no `limit`. Hard cap server-side even if the UI paginates.
- **Counting rows by fetching them** instead of `count`.
- **Heavy RLS policies** with subqueries per row: use `(select auth.uid())` and indexed lookups, or move membership checks into a stable security-definer helper function.
- Supabase: connection pooling (use the pooler / port 6543 for serverless), avoid creating a new client per request in hot paths.

## Frontend
- Fetching in `useEffect` waterfalls (request B waits on A) when they could run in parallel.
- No caching or dedup (consider React Query/SWR, or Next.js `fetch` caching / `revalidate`).
- Large images unoptimized (`<img>` instead of `next/image`, no width/height, multi-MB PNGs).
- Huge dependencies imported for tiny uses (full `lodash`, `moment`, whole icon packs); no dynamic import for heavy components (charts, editors).
- Realtime subscriptions never cleaned up (`removeChannel` / unsubscribe on unmount), causing leaks and duplicate events.
- Missing `key`s or re-render storms from state placed too high.

## Backend / serverless
- Long synchronous work in a request (PDF generation, LLM chains, image processing) that will hit timeouts; move to a queue/background job.
- LLM calls without streaming, timeout, or retry cap.
- No timeouts on outbound fetches.
- Memory leaks from module-level caches that grow unbounded.

## Quick wins to suggest
Add indexes, add pagination caps, `next/image`, parallelize independent awaits with `Promise.all`, set caching headers on static/public data.
