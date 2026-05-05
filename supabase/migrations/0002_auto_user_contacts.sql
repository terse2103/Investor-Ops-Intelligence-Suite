-- 0002_auto_user_contacts.sql
--
-- Extend the signup trigger so every new auth.users row also gets a
-- user_contacts row populated from auth.users.email. Without this, the
-- approval dispatcher cannot resolve a recipient when admins approve the
-- 'email' pending_action and the dispatch fails with
-- "no recipient email configured for booking user" (services/approvals/
-- dispatcher.py:_user_email_for_call).
--
-- Idempotent: safe to re-run. Backfills any users who signed up before this.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (id, role)
    values (new.id, 'user')
    on conflict (id) do nothing;

    if new.email is not null then
        insert into public.user_contacts (user_id, email)
        values (new.id, new.email)
        on conflict (user_id) do nothing;
    end if;

    return new;
end;
$$;

-- Backfill: fix any pre-existing users who signed up before this trigger
-- shipped (otherwise the email-action dispatch keeps failing for them).
insert into public.user_contacts (user_id, email)
select u.id, u.email
from auth.users u
where u.email is not null
on conflict (user_id) do nothing;
