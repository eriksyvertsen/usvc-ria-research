"""Build the prospecting workbook from data/scored.csv."""
import datetime as dt

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

OUT = "USVC_RIA_Lead_List.xlsx"
df = pd.read_csv("data/scored.csv")

df["aum_mm"] = (df["raum"] / 1e6).round(0)
df["avg_account_k"] = (df["avg_account"] / 1e3).round(0)
df["address"] = (df["address1"].fillna("") + " " + df["address2"].fillna("")).str.strip()

cols = {
    "lead_score": "Lead Score",
    "tier": "Venture Fit Tier",
    "firm_name": "Firm",
    "crd": "CRD",
    "city": "City",
    "state": "State",
    "aum_mm": "Reg. AUM ($M)",
    "hnw_share": "HNW % of AUM",
    "hnw_indiv_share": "Indiv+HNW % of AUM",
    "avg_account_k": "Avg Account ($K)",
    "accounts": "Accounts",
    "employees": "Employees",
    "advisory_staff": "Advisory Staff",
    "other_offices": "Branch Offices",
    "main_phone": "Main Phone",
    "website": "Website",
    "cco_name": "CCO (from brochure)",
    "principals": "Principals / Execs (from brochure)",
    "contact_emails": "Named Emails (from brochure)",
    "generic_emails": "Firm Inbox Emails",
    "brochure_phones": "Brochure Phones",
    "vc_active_mentions": "Venture: Firm-Activity Mentions",
    "vc_mentions": "Venture: Total Mentions",
    "pm_mentions": "Private Mkts/Alts Mentions",
    "alt_platforms_named": "Alt Platforms / Managers Named",
    "primary_custodian": "Primary Custodian",
    "custodians_named": "Custodians Named (mentions)",
    "vc_terms_found": "Venture Terms Found",
    "pm_terms_found": "Private Mkts Terms Found",
    "vc_evidence": "Venture Evidence (brochure excerpts)",
    "pm_evidence": "Private Mkts Evidence (brochure excerpts)",
    "accredited_qp_mentions": "Accredited/QP Mentions",
    "mentions_usvc": "Mentions USVC",
    "is_broker_dealer_affiliated": "BD-Affiliated",
    "sponsors_wrap": "Wrap Sponsor",
    "advises_private_funds": "Advises Private Funds",
    "n_vc_funds": "# VC Funds Advised",
    "n_pe_funds": "# PE Funds Advised",
    "disciplinary_disclosure": "Disciplinary Disclosure",
    "org_form": "Org Form",
    "latest_adv_filing": "Latest ADV Filing",
    "brochure_date": "Brochure Date",
    "brochure_names": "Brochures Reviewed",
    "address": "Address",
    "zip": "ZIP",
    "iapd_url": "IAPD Profile",
    "brochure_url": "Brochure PDF",
}
out = df[list(cols)].rename(columns=cols)
leads = out[out["Venture Fit Tier"].str[0].isin(["A", "B", "C"])]

tier_summary = (
    df.groupby("tier")
    .agg(firms=("crd", "count"), total_aum_bn=("raum", lambda x: round(x.sum() / 1e9, 1)),
         median_aum_mm=("raum", lambda x: round(x.median() / 1e6)), with_named_email=("contact_emails", lambda x: x.notna().sum()),
         with_cco_name=("cco_name", lambda x: x.notna().sum()))
    .reset_index().rename(columns={"tier": "Tier"})
)
state_summary = (
    df[df["tier"].str[0].isin(["A", "B", "C"])].groupby("state")
    .agg(firms=("crd", "count"), aum_bn=("raum", lambda x: round(x.sum() / 1e9, 1)),
         tier_a=("tier", lambda x: (x.str[0] == "A").sum()))
    .sort_values("aum_bn", ascending=False).reset_index()
)

today = dt.date.today().isoformat()
readme = pd.DataFrame({"USVC RIA Lead List": [
    f"Built {today} from SEC public data.",
    "",
    "SOURCES",
    "• SEC 'Information About Registered Investment Advisers' monthly file (data as of Sept/Oct 2026): AUM, client mix, addresses, phones, websites, Items 5–11.",
    "• Each firm's current Form ADV Part 2A brochure(s) from IAPD (adviserinfo.sec.gov), up to the 4 most recent per firm, text-mined.",
    "",
    "UNIVERSE (who was screened)",
    "• SEC-registered RIAs, US main office, regulatory AUM ≥ $250M, and ≥ 40% of AUM from individual + high-net-worth clients (Item 5.D).",
    "",
    "VENTURE FIT TIERS",
    "• A - Venture explicit: brochure describes venture / early-stage / pre-IPO / private-company investing as something the firm or its clients do (≥2 such passages, or 1 plus alt platforms or deep private-markets language).",
    "• B - Venture mentioned: venture language appears, but mostly in risk disclosures or passing references.",
    "• C - Private markets / alts: no venture language, but meaningful private equity / private credit / interval fund / alt-platform use.",
    "• D - Alts mentioned (light), E - No alts signal: in the 'All Screened' tab only.",
    "",
    "LEAD SCORE (0–100)",
    "• Venture language (0–30): firm-activity passages weighted 4 pts each (max 5), any mention 1 pt (max 10).",
    "• Private-markets depth (0–15), alt platforms named such as iCapital, CAIS or Moonfare (0–10), accredited/QP language (3), advises its own PE/VC funds (2).",
    "• Size: log-scaled AUM, $250M→0 to $20B+→15. HNW concentration (0–10). Avg account size (0–5). ≥80% discretionary (5).",
    "• Penalties: broker-dealer affiliated (−5, centralized product shelf); disciplinary disclosure (−3).",
    "",
    "CONTACT DATA — CAVEATS",
    "• Main phone and website come from Form ADV Item 1. CCO, principals and emails are pulled automatically from brochure text and may be incomplete or occasionally wrong. Verify before outreach.",
    "• Large/wirehouse firms rarely list individual contacts in Part 2A. Use the IAPD link, LinkedIn, or a data vendor for those.",
    "• Brochure excerpts are short quotes from public SEC filings, included as evidence for the tier.",
    "• Wirehouses and BD-affiliated platforms (Morgan Stanley, Merrill, etc.) are included but sold through home-office due diligence, not individual advisors.",
]})

with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
    readme.to_excel(xw, sheet_name="README", index=False)
    leads.to_excel(xw, sheet_name="Leads (Tier A-C)", index=False)
    out.to_excel(xw, sheet_name="All Screened", index=False)
    tier_summary.to_excel(xw, sheet_name="Summary by Tier", index=False)
    state_summary.to_excel(xw, sheet_name="Leads by State", index=False)

wb = load_workbook(OUT)
widths = {"Firm": 38, "Venture Evidence (brochure excerpts)": 80, "Private Mkts Evidence (brochure excerpts)": 60,
          "Principals / Execs (from brochure)": 34, "Named Emails (from brochure)": 34, "Firm Inbox Emails": 30,
          "Website": 30, "Venture Terms Found": 40, "Private Mkts Terms Found": 40, "Brochures Reviewed": 40,
          "Alt Platforms / Managers Named": 30, "Primary Custodian": 18, "Custodians Named (mentions)": 40, "Address": 34, "IAPD Profile": 22, "Brochure PDF": 22,
          "Venture Fit Tier": 24, "CCO (from brochure)": 24}
fmt = {"Reg. AUM ($M)": "#,##0", "Avg Account ($K)": "#,##0", "Accounts": "#,##0", "HNW % of AUM": "0%",
       "Indiv+HNW % of AUM": "0%", "Employees": "#,##0", "Advisory Staff": "#,##0"}
tier_fill = {"A": "C6EFCE", "B": "FFEB9C", "C": "DDEBF7"}
for name in ("Leads (Tier A-C)", "All Screened"):
    ws = wb[name]
    hdr = [c.value for c in ws[1]]
    for i, h in enumerate(hdr, 1):
        col = get_column_letter(i)
        ws.column_dimensions[col].width = widths.get(h, 14)
        if h in fmt:
            for cell in ws[col][1:]:
                cell.number_format = fmt[h]
        if h in ("IAPD Profile", "Brochure PDF"):
            for cell in ws[col][1:]:
                if cell.value:
                    cell.hyperlink = cell.value
                    cell.value = "Open"
                    cell.font = Font(color="0563C1", underline="single")
    ti = hdr.index("Venture Fit Tier") + 1
    for row in ws.iter_rows(min_row=2):
        t = (row[ti - 1].value or "")[:1]
        if t in tier_fill:
            row[ti - 1].fill = PatternFill("solid", fgColor=tier_fill[t])
    ws.freeze_panes = "D2"
    ref = f"A1:{get_column_letter(len(hdr))}{ws.max_row}"
    tab = Table(displayName=name.split()[0].replace("(", "") + "Tbl", ref=ref)
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(tab)
ws = wb["README"]
ws.column_dimensions["A"].width = 160
for cell in ws["A"]:
    cell.alignment = Alignment(wrap_text=True, vertical="top")
ws["A1"].font = Font(bold=True, size=14)
for name in ("Summary by Tier", "Leads by State"):
    for i in range(1, 8):
        wb[name].column_dimensions[get_column_letter(i)].width = 22
wb.save(OUT)
print(f"wrote {OUT}: {len(leads)} leads, {len(out)} screened")
