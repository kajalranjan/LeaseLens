# Supabase accounts (optional)

LeaseLens turns on real accounts only when `SUPABASE_URL` and `SUPABASE_KEY` are set in Streamlit secrets.
Without them it uses a demo login, so the app always runs.

1. Authentication → Sign In / Providers → Email: turn off "Confirm email" (for demos), Save.
2. SQL Editor → New query → run:

```sql
create table if not exists public.reports (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  kind text not null,
  summary text not null,
  data jsonb not null,
  created_at timestamptz not null default now()
);
alter table public.reports enable row level security;
create policy "Users read own reports"   on public.reports for select using (auth.uid() = user_id);
create policy "Users add own reports"    on public.reports for insert with check (auth.uid() = user_id);
create policy "Users delete own reports" on public.reports for delete using (auth.uid() = user_id);
grant select, insert, delete on public.reports to authenticated;
```

3. Project Settings → API Keys: copy the **publishable** (or legacy **anon**) key. Never use the secret / service_role key.
4. Streamlit secrets:
```toml
SUPABASE_URL = "https://<project>.supabase.co"
SUPABASE_KEY = "sb_publishable_..."
```
