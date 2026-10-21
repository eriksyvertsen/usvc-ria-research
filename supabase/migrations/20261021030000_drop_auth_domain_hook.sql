-- Rolled back Google sign-in; dashboard is public. Remove the signup domain hook.
drop function if exists public.hook_restrict_signup_domain(jsonb);
