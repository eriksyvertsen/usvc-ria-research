alter table public.firms add column if not exists custodians_named text;
alter table public.firms add column if not exists primary_custodian text;
create index if not exists firms_primary_custodian_idx on public.firms (primary_custodian);
