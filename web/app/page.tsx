import { latestRun, listFirms } from "@/lib/db";
import Explorer from "./explorer";

export const revalidate = 120;

export default async function Page() {
  const [firms, run] = await Promise.all([listFirms(), latestRun()]);
  return (
    <main className="wrap">
      <h1>RIA Venture Leads</h1>
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
