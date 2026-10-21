import { requireUser } from "@/lib/auth";
import { latestRun, listFirms } from "@/lib/db";
import Explorer from "./explorer";

export const dynamic = "force-dynamic";

export default async function Page() {
  const user = await requireUser();
  const [firms, run] = await Promise.all([listFirms(), latestRun()]);
  return (
    <main className="wrap">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
        <h1>RIA Venture Leads</h1>
        <form action="/auth/signout" method="post" className="muted" style={{ fontSize: 12 }}>
          {user.email} · <button className="btn ghost" style={{ padding: "2px 8px", fontSize: 12 }}>Sign out</button>
        </form>
      </div>
      <p className="sub">
        SEC-registered wealth-channel RIAs ($250M+ AUM, ≥40% individual/HNW), screened from current Form ADV Part 2
        brochures for venture and private-markets fit.
        {run && (
          <> Last sync {new Date(run.ran_at).toLocaleString("en-US", { timeZone: "America/New_York" })} ET.</>
        )}
      </p>
      <Explorer firms={firms} run={run} />
    </main>
  );
}
