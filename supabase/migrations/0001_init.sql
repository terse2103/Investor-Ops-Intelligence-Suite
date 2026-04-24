-- 0001_init.sql — Investor Ops & Intelligence Suite initial schema.
-- Run this in the Supabase SQL Editor after creating the project.
-- Creates 11 tables, RLS policies, and an auth trigger that auto-creates a
-- default 'user' profile row on signup. Backend uses the service-role key to
-- bypass RLS for writes.

-- ============================================================================
-- Extensions
-- ============================================================================
create extension if not exists pgcrypto;

-- ============================================================================
-- Tables
-- ============================================================================

-- 1. Profiles (role-bearing extension of auth.users).
create table public.profiles (
    id uuid primary key references auth.users on delete cascade,
    role text not null default 'user' check (role in ('user', 'admin')),
    created_at timestamptz not null default now()
);

-- 2. User contacts (notification email for booking decisions).
create table public.user_contacts (
    user_id uuid primary key references public.profiles on delete cascade,
    email text not null,
    updated_at timestamptz not null default now()
);

-- 3. Sources (RAG corpus registry: M1 MF factsheets + M2 fee scenarios).
create table public.sources (
    id uuid primary key default gen_random_uuid(),
    url text not null unique,
    title text not null,
    category text not null check (category in ('mf_factsheet', 'fee_scenario', 'other')),
    fetched_at timestamptz not null default now(),
    content_hash text
);

-- 4. Reviews (Play Store reviews; filtered at ingest per R-PULSE7).
create table public.reviews (
    play_review_id text primary key,
    user_name text,
    rating int check (rating between 1 and 5),
    content text not null,
    posted_at timestamptz not null,
    scraped_at timestamptz not null default now()
);
create index reviews_posted_at_idx on public.reviews (posted_at desc);

-- 5. Scrape runs (audit row per scrape; holds filtered_out_count).
create table public.scrape_runs (
    id uuid primary key default gen_random_uuid(),
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null check (status in ('running', 'ok', 'rate_limited', 'error')),
    review_count int not null default 0,
    filtered_out_count int not null default 0,
    trigger_source text check (trigger_source in ('manual', 'cron')),
    error_message text
);

-- 6. Pulses (weekly generated pulses).
create table public.pulses (
    id uuid primary key default gen_random_uuid(),
    generated_at timestamptz not null default now(),
    window_start timestamptz not null,
    window_end timestamptz not null,
    themes jsonb not null,
    quotes jsonb not null,
    actions jsonb not null,
    note_text text not null,
    word_count int not null
);
create index pulses_generated_at_idx on public.pulses (generated_at desc);

-- 7. Current themes cache (singleton row for Vapi dynamic-variable injection).
create table public.current_themes (
    id int primary key default 1 check (id = 1),
    pulse_id uuid references public.pulses,
    themes jsonb not null default '[]'::jsonb,
    updated_at timestamptz not null default now()
);
insert into public.current_themes (id, themes) values (1, '[]'::jsonb);

-- 8. Calls (Vapi call metadata).
create table public.calls (
    id text primary key,  -- Vapi call ID
    user_id uuid references public.profiles,
    intent text check (intent in ('book_new', 'reschedule', 'cancel')),
    topic text,
    transcript text,
    booking_code text,
    status text not null default 'in_progress'
        check (status in ('in_progress', 'completed', 'abandoned')),
    started_at timestamptz not null default now(),
    ended_at timestamptz
);
create index calls_user_id_idx on public.calls (user_id);

-- 9. Pending actions (HITL queue).
create table public.pending_actions (
    id uuid primary key default gen_random_uuid(),
    call_id text references public.calls,
    type text not null check (type in ('calendar', 'sheets', 'email')),
    payload jsonb not null,
    status text not null default 'pending'
        check (status in ('pending', 'approved', 'rejected', 'executed', 'failed')),
    created_at timestamptz not null default now(),
    decided_at timestamptz,
    executed_at timestamptz,
    decided_by uuid references public.profiles
);
create index pending_actions_status_idx on public.pending_actions (status);

-- 10. Action audit (post-approval execution results).
create table public.action_audit (
    id uuid primary key default gen_random_uuid(),
    pending_action_id uuid references public.pending_actions,
    executed_at timestamptz not null default now(),
    status text not null check (status in ('ok', 'failed')),
    provider_response jsonb,
    error_message text
);

-- 11. Notifications sent (email audit for booking decisions).
create table public.notifications_sent (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.profiles,
    call_id text references public.calls,
    sent_at timestamptz not null default now(),
    status text not null check (status in ('sent', 'bounced', 'provider_error', 'skipped_no_contact')),
    provider_response jsonb
);

-- ============================================================================
-- Auto-create profile row on new auth.users signup
-- ============================================================================
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (id, role) values (new.id, 'user')
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ============================================================================
-- Row Level Security
-- ============================================================================

alter table public.profiles enable row level security;
alter table public.user_contacts enable row level security;
alter table public.sources enable row level security;
alter table public.reviews enable row level security;
alter table public.scrape_runs enable row level security;
alter table public.pulses enable row level security;
alter table public.current_themes enable row level security;
alter table public.calls enable row level security;
alter table public.pending_actions enable row level security;
alter table public.action_audit enable row level security;
alter table public.notifications_sent enable row level security;

-- Helper: is the current user an admin?
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.profiles
        where id = auth.uid() and role = 'admin'
    );
$$;

-- Profiles: users read their own; admins read all.
create policy profiles_self_or_admin_read on public.profiles
    for select using (id = auth.uid() or public.is_admin());

-- User contacts: user manages their own row only.
create policy user_contacts_self_all on public.user_contacts
    for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Sources: any authenticated user can read (needed by RAG chatbot).
create policy sources_authenticated_read on public.sources
    for select using (auth.role() = 'authenticated');

-- Reviews: admin-only read from the client.
create policy reviews_admin_read on public.reviews
    for select using (public.is_admin());

-- Scrape runs: admin-only read.
create policy scrape_runs_admin_read on public.scrape_runs
    for select using (public.is_admin());

-- Pulses: admin-only read.
create policy pulses_admin_read on public.pulses
    for select using (public.is_admin());

-- Current themes: admin-only read (backend uses service-role for Vapi injection).
create policy current_themes_admin_read on public.current_themes
    for select using (public.is_admin());

-- Calls: user reads their own; admin reads all.
create policy calls_self_or_admin_read on public.calls
    for select using (user_id = auth.uid() or public.is_admin());

-- Pending actions: admin-only read.
create policy pending_actions_admin_read on public.pending_actions
    for select using (public.is_admin());

-- Action audit: admin-only read.
create policy action_audit_admin_read on public.action_audit
    for select using (public.is_admin());

-- Notifications sent: admin-only read.
create policy notifications_sent_admin_read on public.notifications_sent
    for select using (public.is_admin());

-- Note: all mutations to reviews/scrape_runs/pulses/current_themes/calls/
-- pending_actions/action_audit/notifications_sent happen via the backend using
-- the service-role key, which bypasses RLS. The frontend never writes directly
-- to these tables (see architecture spec §9.3).
