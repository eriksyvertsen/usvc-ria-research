"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { FirmRow, Run } from "@/lib/db";
import { TIER_COLOR, money, pct, site } from "./format";

type SortKey = "lead_score" | "raum" | "firm_name" | "state" | "hnw_share" | "avg_account" | "vc_mentions" | "pm_mentions";
const PAGE = 100;

export default function Explorer({ firms, run }: { firms: FirmRow[]; run: Run | null }) {
  const [q, setQ] = useState("");
  const [tiers, setTiers] = useState<Set<string>>(new Set(["A", "B", "C"]));
  const [state, setState] = useState("");
  const [minAum, setMinAum] = useState(0);
  const [minScore, setMinScore] = useState(0);
  const [platform, setPlatform] = useState("");
  const [custodian, setCustodian] = useState("");
  const [custodianMode, setCustodianMode] = useState<"primary" | "any">("primary");
  const [hasContact, setHasContact] = useState(false);
  const [noBD, setNoBD] = useState(false);
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "lead_score", dir: -1 });
  const [page, setPage] = useState(0);

  const states = useMemo(() => [...new Set(firms.map((f) => f.state).filter(Boolean))].sort() as string[], [firms]);
  const platforms = useMemo(() => {
    const c = new Map<string, number>();
    firms.forEach((f) => f.alt_platforms_named?.split("; ").forEach((p) => p && c.set(p, (c.get(p) ?? 0) + 1)));
    return [...c.entries()].sort((a, b) => b[1] - a[1]);
  }, [firms]);

  const custodianNames = (f: FirmRow) =>
    (f.custodians_named ?? "").split("; ").filter(Boolean).map((c) => c.replace(/ \(\d+\)$/, ""));
  const custodians = useMemo(() => {
    const c = new Map<string, number>();
    firms.forEach((f) => custodianNames(f).forEach((n) => c.set(n, (c.get(n) ?? 0) + 1)));
    return [...c.entries()].sort((a, b) => b[1] - a[1]);
  }, [firms]);

  const tierCounts = useMemo(() => {
    const c = new Map<string, { n: number; aum: number; label: string }>();
    firms.forEach((f) => {
      const t = f.tier ?? "P - Brochure pending";
      const k = t[0];
      const cur = c.get(k) ?? { n: 0, aum: 0, label: t };
      cur.n += 1;
      cur.aum += f.raum ?? 0;
      c.set(k, cur);
    });
    return [...c.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [firms]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const rows = firms.filter((f) => {
      if (tiers.size && !tiers.has((f.tier ?? "P")[0])) return false;
      if (state && f.state !== state) return false;
      if ((f.raum ?? 0) < minAum * 1e6) return false;
      if ((f.lead_score ?? 0) < minScore) return false;
      if (platform && !(f.alt_platforms_named ?? "").split("; ").includes(platform)) return false;
      if (custodian && (custodianMode === "primary" ? f.primary_custodian !== custodian : !custodianNames(f).includes(custodian))) return false;
      if (hasContact && !(f.cco_name || f.contact_emails || f.principals)) return false;
      if (noBD && f.is_broker_dealer_affiliated) return false;
      if (needle) {
        const hay = `${f.firm_name} ${f.city} ${f.state} ${f.cco_name ?? ""} ${f.principals ?? ""} ${f.crd}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
    const { key, dir } = sort;
    rows.sort((a, b) => {
      const x = a[key] ?? -Infinity;
      const y = b[key] ?? -Infinity;
      return (x < y ? -1 : x > y ? 1 : 0) * dir;
    });
    return rows;
  }, [firms, q, tiers, state, minAum, minScore, platform, custodian, custodianMode, hasContact, noBD, sort]);

  const topCustodians = useMemo(() => {
    const c = new Map<string, number>();
    filtered.forEach((f) => f.primary_custodian && c.set(f.primary_custodian, (c.get(f.primary_custodian) ?? 0) + 1));
    return [...c.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
  }, [filtered]);

  const topStates = useMemo(() => {
    const c = new Map<string, number>();
    filtered.forEach((f) => f.state && c.set(f.state, (c.get(f.state) ?? 0) + 1));
    return [...c.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
  }, [filtered]);

  const totalAum = filtered.reduce((s, f) => s + (f.raum ?? 0), 0);
  const withContact = filtered.filter((f) => f.cco_name || f.contact_emails).length;
  const done = run ? run.firms_total - run.firms_pending : 0;
  const pageRows = filtered.slice(page * PAGE, page * PAGE + PAGE);
  const maxTier = Math.max(...tierCounts.map(([, v]) => v.n), 1);
  const maxState = Math.max(...topStates.map(([, n]) => n), 1);
  const maxCust = Math.max(...topCustodians.map(([, n]) => n), 1);

  const toggleTier = (t: string) => {
    const n = new Set(tiers);
    n.has(t) ? n.delete(t) : n.add(t);
    setTiers(n);
    setPage(0);
  };
  const sortBy = (key: SortKey) => setSort((s) => ({ key, dir: s.key === key ? ((-s.dir) as 1 | -1) : -1 }));
  const arrow = (key: SortKey) => (sort.key === key ? (sort.dir === -1 ? " ↓" : " ↑") : "");

  function exportCsv() {
    const cols: (keyof FirmRow)[] = ["crd", "firm_name", "tier", "lead_score", "city", "state", "raum", "hnw_share",
      "avg_account", "main_phone", "website", "cco_name", "principals", "contact_emails", "generic_emails",
      "vc_active_mentions", "vc_mentions", "pm_mentions", "alt_platforms_named", "primary_custodian", "custodians_named",
      "is_broker_dealer_affiliated"];
    const esc = (v: unknown) => (v == null ? "" : `"${String(v).replace(/"/g, '""')}"`);
    const csv = [cols.join(","), ...filtered.map((f) => cols.map((c) => esc(f[c])).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `ria-leads-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  }

  return (
    <>
      <section className="kpis">
        <div className="kpi">
          <div className="label">Firms in view</div>
          <div className="value num">{filtered.length.toLocaleString()}</div>
          <div className="hint">of {firms.length.toLocaleString()} screened</div>
        </div>
        <div className="kpi">
          <div className="label">AUM in view</div>
          <div className="value num">{money(totalAum)}</div>
          <div className="hint">regulatory AUM, Form ADV 5.F</div>
        </div>
        <div className="kpi">
          <div className="label">Tier A — venture explicit</div>
          <div className="value num">{(tierCounts.find(([k]) => k === "A")?.[1].n ?? 0).toLocaleString()}</div>
          <div className="hint">across all screened firms</div>
        </div>
        <div className="kpi">
          <div className="label">With a named contact</div>
          <div className="value num">{withContact.toLocaleString()}</div>
          <div className="hint">CCO or email found in brochure</div>
        </div>
        <div className="kpi">
          <div className="label">Brochures analyzed</div>
          <div className="value num">{run ? `${done.toLocaleString()} / ${run.firms_total.toLocaleString()}` : "—"}</div>
          <div className="progress"><div style={{ width: `${run ? (100 * done) / run.firms_total : 0}%` }} /></div>
        </div>
      </section>

      <section className="panels">
        <div className="panel">
          <h2>Venture fit tiers (click to filter)</h2>
          {tierCounts.map(([k, v]) => (
            <div className="bar-row" key={k}>
              <button onClick={() => toggleTier(k)} style={{ opacity: tiers.has(k) ? 1 : 0.5 }}>
                {v.label}
              </button>
              <div className="bar-track">
                <div className="bar" style={{ width: `${(100 * v.n) / maxTier}%`, background: TIER_COLOR[k] }} />
              </div>
              <span className="num right">{v.n.toLocaleString()}</span>
            </div>
          ))}
        </div>
        <div className="panel">
          <h2>Top states in view</h2>
          {topStates.map(([s, n]) => (
            <div className="bar-row" key={s}>
              <button onClick={() => { setState(state === s ? "" : s); setPage(0); }}>{s}</button>
              <div className="bar-track">
                <div className="bar" style={{ width: `${(100 * n) / maxState}%`, background: "var(--accent)" }} />
              </div>
              <span className="num right">{n.toLocaleString()}</span>
            </div>
          ))}
        </div>
        <div className="panel">
          <h2>Primary custodian in view (click to filter)</h2>
          {topCustodians.map(([c, n]) => (
            <div className="bar-row" key={c}>
              <button onClick={() => { setCustodianMode("primary"); setCustodian(custodian === c ? "" : c); setPage(0); }}
                style={{ opacity: !custodian || custodian === c ? 1 : 0.5 }}>{c}</button>
              <div className="bar-track">
                <div className="bar" style={{ width: `${(100 * n) / maxCust}%`, background: "var(--tier-b)" }} />
              </div>
              <span className="num right">{n.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="filters">
        <input type="search" placeholder="Search firm, city, CCO, principal, CRD…" value={q}
          onChange={(e) => { setQ(e.target.value); setPage(0); }} />
        <label>Tiers
          {["A", "B", "C", "D", "E", "P"].map((t) => (
            <span key={t}>
              <input type="checkbox" checked={tiers.has(t)} onChange={() => toggleTier(t)} /> {t}
            </span>
          ))}
        </label>
        <select value={state} onChange={(e) => { setState(e.target.value); setPage(0); }}>
          <option value="">All states</option>
          {states.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select value={minAum} onChange={(e) => { setMinAum(+e.target.value); setPage(0); }}>
          <option value={0}>Any AUM</option>
          <option value={500}>$500M+</option>
          <option value={1000}>$1B+</option>
          <option value={5000}>$5B+</option>
          <option value={20000}>$20B+</option>
        </select>
        <label>Min score
          <input type="number" min={0} max={100} value={minScore} style={{ width: 64 }}
            onChange={(e) => { setMinScore(+e.target.value); setPage(0); }} />
        </label>
        <select value={platform} onChange={(e) => { setPlatform(e.target.value); setPage(0); }}>
          <option value="">Any alt platform</option>
          {platforms.map(([p, n]) => <option key={p} value={p}>{p} ({n})</option>)}
        </select>
        <select value={custodian} onChange={(e) => { setCustodian(e.target.value); setPage(0); }}>
          <option value="">Any custodian</option>
          {custodians.map(([c, n]) => <option key={c} value={c}>{c} ({n})</option>)}
        </select>
        {custodian && (
          <select value={custodianMode} onChange={(e) => { setCustodianMode(e.target.value as "primary" | "any"); setPage(0); }}>
            <option value="primary">as primary</option>
            <option value="any">mentioned anywhere</option>
          </select>
        )}
        <label><input type="checkbox" checked={hasContact} onChange={(e) => { setHasContact(e.target.checked); setPage(0); }} /> Has named contact</label>
        <label><input type="checkbox" checked={noBD} onChange={(e) => { setNoBD(e.target.checked); setPage(0); }} /> Exclude BD-affiliated</label>
        <button className="btn" onClick={exportCsv}>Export CSV</button>
      </section>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th onClick={() => sortBy("lead_score")} className="right">Score{arrow("lead_score")}</th>
              <th>Tier</th>
              <th onClick={() => sortBy("firm_name")}>Firm{arrow("firm_name")}</th>
              <th onClick={() => sortBy("state")}>Location{arrow("state")}</th>
              <th onClick={() => sortBy("raum")} className="right">AUM{arrow("raum")}</th>
              <th onClick={() => sortBy("hnw_share")} className="right">HNW %{arrow("hnw_share")}</th>
              <th onClick={() => sortBy("avg_account")} className="right">Avg acct{arrow("avg_account")}</th>
              <th onClick={() => sortBy("vc_mentions")} className="right">VC refs{arrow("vc_mentions")}</th>
              <th onClick={() => sortBy("pm_mentions")} className="right">Alts refs{arrow("pm_mentions")}</th>
              <th>Platforms</th>
              <th>Custodian</th>
              <th>Contact</th>
              <th>Phone</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((f) => {
              const t = (f.tier ?? "P")[0];
              return (
                <tr key={f.crd}>
                  <td className="right num">{f.lead_score?.toFixed(0) ?? "—"}</td>
                  <td><span className="tier" style={{ background: TIER_COLOR[t] }} title={f.tier ?? ""}>{t}</span></td>
                  <td>
                    <Link href={`/firm/${f.crd}`}>{f.firm_name}</Link>
                    {f.is_broker_dealer_affiliated && <span className="chip" title="Broker-dealer affiliated">BD</span>}
                    {f.mentions_usvc && <span className="chip">USVC</span>}
                    {site(f.website) && <> <a className="muted" href={site(f.website)!} target="_blank" rel="noreferrer">↗</a></>}
                  </td>
                  <td>{f.city}, {f.state}</td>
                  <td className="right num">{money(f.raum)}</td>
                  <td className="right num">{pct(f.hnw_share)}</td>
                  <td className="right num">{money(f.avg_account)}</td>
                  <td className="right num">{f.vc_active_mentions}/{f.vc_mentions}</td>
                  <td className="right num">{f.pm_mentions}</td>
                  <td className="wrap-cell">{f.alt_platforms_named?.split("; ").map((p) => <span className="chip" key={p}>{p}</span>)}</td>
                  <td>{f.primary_custodian ?? <span className="muted">—</span>}</td>
                  <td className="wrap-cell">
                    {f.cco_name && <div>{f.cco_name} <span className="muted">(CCO)</span></div>}
                    {f.contact_emails && <div><a href={`mailto:${f.contact_emails.split("; ")[0]}`}>{f.contact_emails.split("; ")[0]}</a></div>}
                    {!f.cco_name && !f.contact_emails && f.principals && <div className="muted">{f.principals.split("; ")[0]}</div>}
                  </td>
                  <td className="num">{f.main_phone}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="pager">
          <span className="muted">
            {filtered.length ? `${page * PAGE + 1}–${Math.min(filtered.length, (page + 1) * PAGE)} of ${filtered.length.toLocaleString()}` : "No firms match"}
          </span>
          <button className="btn ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>Prev</button>
          <button className="btn ghost" disabled={(page + 1) * PAGE >= filtered.length} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      </div>
    </>
  );
}
