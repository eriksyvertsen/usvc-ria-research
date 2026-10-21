-- USVC RIA prospecting database
create table if not exists public.firms (
  crd                bigint primary key,
  sec_number         text,
  firm_name          text not null,
  legal_name         text,
  address1           text,
  address2           text,
  city               text,
  state              text,
  zip                text,
  main_phone         text,
  website            text,
  latest_adv_filing  text,
  org_form           text,
  raum               double precision,
  raum_discretionary double precision,
  accounts           bigint,
  avg_account        double precision,
  indiv_clients      double precision,
  hnw_clients        double precision,
  indiv_aum          double precision,
  hnw_aum            double precision,
  hnw_indiv_share    double precision,
  hnw_share          double precision,
  employees          double precision,
  advisory_staff     double precision,
  other_offices      double precision,
  is_broker_dealer_affiliated boolean,
  is_insurance_affiliated     boolean,
  sponsors_wrap               boolean,
  advises_private_funds       boolean,
  n_private_funds    bigint,
  n_vc_funds         double precision,
  n_pe_funds         double precision,
  private_fund_gav   double precision,
  any_vc_funds       boolean,
  any_pe_funds       boolean,
  recommends_securities_with_interest boolean,
  disciplinary_disclosure boolean,
  brochure_names     text,
  brochure_date      text,
  brochure_status    text,
  brochure_version_ids text,
  brochure_chars     bigint,
  vc_mentions        int default 0,
  vc_active_mentions int default 0,
  pm_mentions        int default 0,
  vc_terms_found     text,
  pm_terms_found     text,
  alt_platforms_named text,
  n_platforms        int default 0,
  accredited_qp_mentions int default 0,
  mentions_usvc      boolean,
  vc_evidence        text,
  pm_evidence        text,
  contact_emails     text,
  generic_emails     text,
  brochure_phones    text,
  cco_name           text,
  principals         text,
  tier               text,
  lead_score         double precision,
  iapd_url           text,
  brochure_url       text,
  updated_at         timestamptz default now()
);
create index if not exists firms_score_idx on public.firms (lead_score desc);
create index if not exists firms_tier_idx  on public.firms (tier);
create index if not exists firms_state_idx on public.firms (state);

create table if not exists public.pipeline_runs (
  id            bigserial primary key,
  ran_at        timestamptz default now(),
  firms_total   int,
  firms_with_brochure int,
  firms_pending int,
  brochures_downloaded int,
  note          text
);

-- Private by default: RLS on, no policies => anon/authenticated roles can't read.
-- The dashboard reads server-side with the service-role key.
alter table public.firms enable row level security;
alter table public.pipeline_runs enable row level security;
revoke all on public.firms, public.pipeline_runs from anon, authenticated;
