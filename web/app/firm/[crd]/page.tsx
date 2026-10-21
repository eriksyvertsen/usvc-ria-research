import Link from "next/link";
import { notFound } from "next/navigation";
import { getFirm } from "@/lib/db";
import { TIER_COLOR, money, pct, site } from "../../format";

export const revalidate = 120;

type F = Record<string, any>;

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  if (v == null || v === "" || v === false) return null;
  return (<><dt>{k}</dt><dd>{v === true ? "Yes" : v}</dd></>);
}

export default async function FirmPage({ params }: { params: Promise<{ crd: string }> }) {
  const { crd } = await params;
  const f = (await getFirm(Number(crd))) as F | null;
  if (!f) notFound();
  const t = (f.tier ?? "P")[0];
  const evidence = (s: string | null) => (s ? s.split(" || ") : []);
  const emails = (s: string | null) => s?.split("; ").map((e: string) => (
    <div key={e}><a href={`mailto:${e}`}>{e}</a></div>
  ));

  return (
    <main className="wrap">
      <p><Link href="/">← All firms</Link></p>
      <h1>{f.firm_name}</h1>
      <p className="sub">
        <span className="tier" style={{ background: TIER_COLOR[t] }}>{f.tier}</span>{" "}
        Lead score <b className="num">{f.lead_score?.toFixed(0)}</b> · {f.city}, {f.state} · CRD {f.crd}
      </p>

      <div className="detail-grid">
        <section className="panel">
          <h2>Contact</h2>
          <dl>
            <Row k="Main phone" v={f.main_phone} />
            <Row k="Website" v={site(f.website) && <a href={site(f.website)!} target="_blank" rel="noreferrer">{f.website.toLowerCase()}</a>} />
            <Row k="Address" v={[f.address1, f.address2, `${f.city}, ${f.state} ${f.zip ?? ""}`].filter(Boolean).join(", ")} />
            <Row k="CCO (brochure)" v={f.cco_name} />
            <Row k="Principals (brochure)" v={f.principals} />
            <Row k="Named emails" v={emails(f.contact_emails)} />
            <Row k="Firm inboxes" v={emails(f.generic_emails)} />
            <Row k="Brochure phones" v={f.brochure_phones} />
          </dl>
          <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>
            Names and emails are machine-extracted from the brochure. Verify before outreach.
          </p>
        </section>

        <section className="panel">
          <h2>Firm profile (Form ADV Part 1)</h2>
          <dl>
            <Row k="Regulatory AUM" v={money(f.raum)} />
            <Row k="Discretionary AUM" v={money(f.raum_discretionary)} />
            <Row k="Accounts" v={f.accounts?.toLocaleString()} />
            <Row k="Avg account" v={money(f.avg_account)} />
            <Row k="HNW % of AUM" v={pct(f.hnw_share)} />
            <Row k="Indiv + HNW % of AUM" v={pct(f.hnw_indiv_share)} />
            <Row k="Employees / advisory staff" v={`${f.employees ?? "—"} / ${f.advisory_staff ?? "—"}`} />
            <Row k="Branch offices" v={f.other_offices} />
            <Row k="BD-affiliated" v={f.is_broker_dealer_affiliated} />
            <Row k="Wrap sponsor" v={f.sponsors_wrap} />
            <Row k="Advises private funds" v={f.advises_private_funds && `${f.n_private_funds} funds (VC ${f.n_vc_funds ?? 0}, PE ${f.n_pe_funds ?? 0})`} />
            <Row k="Disciplinary disclosure" v={f.disciplinary_disclosure} />
            <Row k="Latest ADV filing" v={f.latest_adv_filing} />
          </dl>
        </section>

        <section className="panel">
          <h2>Venture &amp; private-markets signals</h2>
          <dl>
            <Row k="Venture mentions" v={`${f.vc_mentions} total, ${f.vc_active_mentions} describing firm activity`} />
            <Row k="Venture terms" v={f.vc_terms_found} />
            <Row k="Private-markets mentions" v={f.pm_mentions} />
            <Row k="Private-markets terms" v={f.pm_terms_found} />
            <Row k="Alt platforms / managers" v={f.alt_platforms_named} />
            <Row k="Accredited / QP mentions" v={f.accredited_qp_mentions} />
            <Row k="Mentions USVC" v={f.mentions_usvc} />
          </dl>
        </section>
      </div>

      <section className="panel" style={{ marginTop: 12 }}>
        <h2>Brochure excerpts: venture</h2>
        {evidence(f.vc_evidence).map((e: string, i: number) => <blockquote key={i}>{e}</blockquote>)}
        {!f.vc_evidence && <p className="muted">No venture language found.</p>}
        <h2 style={{ marginTop: 16 }}>Brochure excerpts: private markets</h2>
        {evidence(f.pm_evidence).map((e: string, i: number) => <blockquote key={i}>{e}</blockquote>)}
        {!f.pm_evidence && <p className="muted">No private-markets language found.</p>}
      </section>

      <section className="panel" style={{ marginTop: 12 }}>
        <h2>Sources</h2>
        <dl>
          <Row k="IAPD profile" v={<a href={f.iapd_url} target="_blank" rel="noreferrer">adviserinfo.sec.gov</a>} />
          <Row k="Brochure PDF" v={f.brochure_url && <a href={f.brochure_url} target="_blank" rel="noreferrer">Current Part 2A</a>} />
          <Row k="Brochures reviewed" v={f.brochure_names} />
          <Row k="Brochure date" v={f.brochure_date} />
          <Row k="Last updated" v={f.updated_at && new Date(f.updated_at).toLocaleString("en-US")} />
        </dl>
      </section>
    </main>
  );
}
