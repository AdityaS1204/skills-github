# Supabase checklist

Supabase exposes your database over a public REST/GraphQL API. The `anon` key is meant to be public, so **row level security (RLS) is the only thing between the internet and your tables.** A table without RLS is readable and writable by anyone who has your project URL and anon key (both ship in your frontend bundle).

## 1. RLS on every exposed table (Critical)
- Every table in the `public` schema (or any schema in "Exposed schemas") needs `alter table x enable row level security;`.
- `scripts/check_rls.py` reads the repo's migrations. The live DB can differ, so tell the user to confirm in the dashboard: **Authentication > Policies**, or run:
  ```sql
  select schemaname, tablename, rowsecurity from pg_tables where schemaname = 'public' order by rowsecurity, tablename;
  ```
  Any row with `rowsecurity = false` is wide open.
- RLS enabled with **zero policies** denies all access via the API. That's safe, but usually means the app is broken or policies are missing.

## 2. Policies that are secretly open (Critical)
- `using (true)` or `with check (true)` on insert/update/delete means anyone in that role can write.
- Policies `to anon` / `to public` on anything private.
- Policies that check a column the user controls: `using (user_id = (select user_id from profiles where id = ...))` style tricks, or trusting `user_metadata` from the JWT (users can edit their own `user_metadata`; only `app_metadata` is safe for roles).
- Correct ownership pattern:
  ```sql
  create policy "own rows" on public.notes for all to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
  ```
  Wrapping `auth.uid()` in `(select ...)` also makes it faster.
- `with check` matters on insert/update: without it a user can insert or reassign rows to another user_id.

## 3. Service role key (Critical)
- `SUPABASE_SERVICE_ROLE_KEY` bypasses RLS entirely. It must only exist in server-side code and server env vars. Never in `NEXT_PUBLIC_*`, `EXPO_PUBLIC_*`, `VITE_*`, a client component, a mobile app bundle or a repo.
- Any server route using the service-role client must do its own auth and authorization checks first, because RLS won't.

## 4. Easy-to-miss holes
- **Views** bypass RLS by default (they run as their owner). Use `with (security_invoker = true)` on Postgres 15+, or don't expose them.
- **`security definer` functions** run as the owner. They need `set search_path = ''` (or a fixed schema) and must check `auth.uid()` internally. Anything callable via `supabase.rpc()` is public API.
- **Storage buckets**: public buckets serve every file to anyone with the URL. Check `storage.objects` policies for private buckets; files named after user ids need policies tying path to `auth.uid()`.
- **Realtime**: check which tables are in the `supabase_realtime` publication; row changes broadcast subject to RLS, but only if RLS is on.
- **Auth settings** (dashboard only): email confirmation on, redirect URL allow-list not `*`, signups disabled if the app is invite-only, leaked-password protection on, sensible JWT expiry.
- **Column-level exposure**: RLS is row-level. If a table mixes public and private columns (e.g. `profiles.email`, `stripe_customer_id`), split the table or use a view.
- Don't trust client-sent values for privilege: `role`, `is_admin`, `plan`, `credits` columns must not be writable by the user's own update policy.

## 5. Verify like an attacker (tell the user to do this)
1. Open the app logged out, copy the project URL and anon key from the network tab.
2. `curl "$URL/rest/v1/<table>?select=*" -H "apikey: $ANON" -H "Authorization: Bearer $ANON"` should return `[]` or 401 for private tables.
3. Log in as user A and try to read or update one of user B's rows by id. It must fail.
