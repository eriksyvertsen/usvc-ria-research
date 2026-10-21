# USVC RIA Research

A lead list of wealth-channel RIAs whose strategies include venture capital or private markets, built from SEC Form ADV data.

## Pipeline

| Step | Script | What it does |
|---|---|---|
| 1 | `scripts/01_universe.py` | Filters the SEC monthly adviser CSV to US firms with ≥$250M RAUM and ≥40% of AUM from individual/HNW clients |
| 2 | `scripts/02_fetch_brochures.py` | Downloads each firm's current Part 2A brochures from IAPD (resumable, rate-limited to 1 API call / 2.5s) |
| 3 | `scripts/03_extract_and_score.py` | Extracts brochure text, mines venture/private-markets language and contacts, assigns tier and 0–100 lead score |
| 4 | `scripts/04_build_workbook.py` | Writes `USVC_RIA_Lead_List.xlsx` |
| 5 | `scripts/05_sync_supabase.py` | Re-scores and upserts every firm into Supabase (`firms`, `pipeline_runs`) |
| 6 | `scripts/06_watch_and_sync.sh` | Runs step 5 every 10 min while step 2 is running, then a final sync and the workbook |

Data (`data/`), brochures and secrets (`.env.local`) are not committed.

## Database

The Supabase project `usvc-ria-research` (AngelList Asset Management org). The schema is in `supabase/migrations/`. RLS is on with no anon policies; only the service-role key (server side) can read.

## Dashboard

`web/` is a Next.js app deployed on Vercel. It is public: anyone with the URL can view it. The database is still only readable server-side. It needs `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` set as server env vars.

```bash
cd web && npm install && npm run dev
```
