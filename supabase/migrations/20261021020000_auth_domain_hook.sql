-- Reject sign-ups from anyone outside @angellist.com (Supabase "before user created" auth hook).
create or replace function public.hook_restrict_signup_domain(event jsonb)
returns jsonb
language plpgsql
as $$
declare
  email text := lower(coalesce(event->'user'->>'email', ''));
begin
  if email like '%@angellist.com' then
    return '{}'::jsonb;
  end if;
  return jsonb_build_object('error', jsonb_build_object(
    'http_code', 403,
    'message', 'Only @angellist.com accounts can access this dashboard.'));
end;
$$;

grant execute on function public.hook_restrict_signup_domain(jsonb) to supabase_auth_admin;
revoke execute on function public.hook_restrict_signup_domain(jsonb) from authenticated, anon, public;
