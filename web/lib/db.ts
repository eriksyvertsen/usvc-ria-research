import "server-only";

// Server-only Supabase access. The service-role key never reaches the browser;
// the tables have RLS on with no anon policies.
const URL = process.env.SUPABASE_URL!;
const KEY = process.env.SUPABASE_SERVICE_ROLE_KEY!;

async function rest<T>(path: string, range?: [number, number]): Promise<T> {
  const headers: Record<string, string> = { apikey: KEY, Authorization: `Bearer ${KEY}` };
  if (range) headers.Range = `${range[0]}-${range[1]}`;
  const res = await fetch(`${URL}/rest/v1/${path}`, { headers, next: { revalidate: 120 } });
  if (!res.ok) throw new Error(`Supabase ${res.status}: ${await res.text()}`);
  return res.json();
}

export const LIST_COLS = [
  "crd", "firm_name", "city", "state", "raum", "hnw_share", "hnw_indiv_share", "avg_account", "accounts",
  "employees", "main_phone", "website", "cco_name", "contact_emails", "generic_emails", "tier", "lead_score",
  "vc_mentions", "vc_active_mentions", "pm_mentions", "alt_platforms_named", "is_broker_dealer_affiliated",
  "disciplinary_disclosure", "mentions_usvc", "principals",
] as const;

export type FirmRow = {
  crd: number; firm_name: string; city: string | null; state: string | null; raum: number | null;
  hnw_share: number | null; hnw_indiv_share: number | null; avg_account: number | null; accounts: number | null;
  employees: number | null; main_phone: string | null; website: string | null; cco_name: string | null;
  contact_emails: string | null; generic_emails: string | null; tier: string | null; lead_score: number | null;
  vc_mentions: number; vc_active_mentions: number; pm_mentions: number; alt_platforms_named: string | null;
  is_broker_dealer_affiliated: boolean | null; disciplinary_disclosure: boolean | null; mentions_usvc: boolean | null;
  principals: string | null;
};

export type Run = {
  ran_at: string; firms_total: number; firms_with_brochure: number; firms_pending: number;
  brochures_downloaded: number; note: string;
};

export async function listFirms(): Promise<FirmRow[]> {
  const out: FirmRow[] = [];
  const page = 1000;
  for (let start = 0; ; start += page) {
    const rows = await rest<FirmRow[]>(
      `firms?select=${LIST_COLS.join(",")}&order=lead_score.desc.nullslast,crd.asc`,
      [start, start + page - 1],
    );
    out.push(...rows);
    if (rows.length < page) break;
  }
  return out;
}

export async function getFirm(crd: number): Promise<Record<string, unknown> | null> {
  const rows = await rest<Record<string, unknown>[]>(`firms?crd=eq.${crd}&select=*`);
  return rows[0] ?? null;
}

export async function latestRun(): Promise<Run | null> {
  const rows = await rest<Run[]>("pipeline_runs?select=*&order=ran_at.desc&limit=1");
  return rows[0] ?? null;
}
