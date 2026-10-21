"""Extract brochure text, mine venture / private-markets signals and contacts, score leads.

Inputs:  data/universe.csv, data/brochure_index.csv, data/brochures/<crd>/*.pdf
Outputs: data/text/<crd>/<vid>.txt (cache), data/scored.csv
"""
import csv
import math
import os
import re
import sys
from collections import Counter
from multiprocessing import Pool

import pandas as pd
from pypdf import PdfReader
import logging
logging.getLogger("pypdf").setLevel(logging.ERROR)

BRO = "data/brochures"
TXT = "data/text"

VC_PATTERNS = {
    "venture capital": r"venture[\s-]+capital",
    "venture fund": r"venture\s+funds?",
    "venture investment": r"venture\s+(?:investments?|investing|stage|backed|deals?)",
    "early-stage": r"early[\s-]+stage",
    "startup": r"start[\s-]?ups?\b|emerging\s+growth\s+compan",
    "pre-IPO": r"pre[\s-]?ipo",
    "late-stage private": r"late[\s-]+stage\s+(?:private|compan|growth)",
    "private company stock": r"privately[\s-]+held\s+companies|private\s+compan(?:y|ies)\s+(?:stock|shares|securities|equity)",
    "angel": r"angel\s+invest",
}
PM_PATTERNS = {
    "private equity": r"private\s+equity",
    "private credit": r"private\s+(?:credit|debt|lending)",
    "private markets": r"private\s+markets?",
    "alternative investments": r"alternative\s+(?:investments?|assets?|strateg)",
    "interval fund": r"interval\s+funds?",
    "tender offer fund": r"tender[\s-]+offer\s+funds?",
    "evergreen/semi-liquid": r"evergreen|semi[\s-]liquid",
    "non-traded": r"non[\s-]?traded",
    "BDC": r"business\s+development\s+compan",
    "private funds (third-party)": r"(?:third[\s-]party|unaffiliated)\s+private\s+funds?",
}
PLATFORMS = {
    "iCapital": r"\bicapital\b",
    "CAIS": r"\bcais\b",
    "Moonfare": r"moonfare",
    "Altigo": r"altigo",
    "Yieldstreet": r"yieldstreet",
    "EquityZen": r"equityzen",
    "Forge": r"forge\s+global",
    "AngelList": r"angellist",
    "Fundrise": r"fundrise",
    "Carta": r"\bcarta\b",
    "Hamilton Lane": r"hamilton\s+lane",
    "StepStone": r"stepstone",
    "Destiny Tech100": r"destiny\s+tech",
    "ARK Venture": r"ark\s+venture",
    "Private Shares Fund": r"private\s+shares\s+fund",
    "Augment": r"\baugment\s+(?:markets|private)",
    "Opto": r"\bopto\s+investments",
    "Allocate": r"\ballocate\s+(?:inc|platform)",
    "Juniper Square": r"juniper\s+square",
    "USVC": r"\busvc\b",
}
CUSTODIANS = {
    "Schwab": r"\bschwab\b|td\s+ameritrade",  # TD Ameritrade institutional merged into Schwab
    "Fidelity": r"\bfidelity\b(?!\s+bond)|national\s+financial\s+services",
    "Pershing": r"\bpershing\b",
    "LPL": r"\blpl\b",
    "Raymond James": r"raymond\s+james",
    "Altruist": r"\baltruist\b",
    "Interactive Brokers": r"interactive\s+brokers",
    "Apex Clearing": r"apex\s+(?:clearing|fintech)",
    "StoneX": r"\bstonex\b",
    "Goldman Sachs Custody": r"goldman\s+sachs\s+(?:custody|advisor\s+solutions)",
    "SEI Private Trust": r"sei\s+private\s+trust",
    "Axos": r"\baxos\b",
    "Northern Trust": r"northern\s+trust",
    "BNY Mellon": r"bny\s+mellon|bank\s+of\s+new\s+york\s+mellon",
    "State Street": r"state\s+street\s+(?:bank|corporation|custody)",
    "U.S. Bank": r"u\.?\s?s\.?\s+bank\b",
    "Wells Fargo": r"wells\s+fargo",
    "J.P. Morgan": r"j\.?\s?p\.?\s+morgan|jpmorgan",
    "Morgan Stanley": r"morgan\s+stanley",
    "Merrill / BofA": r"\bmerrill\b|bank\s+of\s+america",
    "UBS": r"\bubs\b",
    # alternative-asset / self-directed custodians: can hold private funds
    "Equity Trust": r"equity\s+trust\s+company",
    "Millennium Trust / Inspira": r"millennium\s+trust|inspira\s+financial",
    "Kingdom Trust": r"kingdom\s+trust",
    "Pensco / Forge Trust": r"\bpensco\b|forge\s+trust",
}
ALT_CUSTODIANS = {"Equity Trust", "Millennium Trust / Inspira", "Kingdom Trust", "Pensco / Forge Trust"}
ACCRED = r"accredited\s+investors?|qualified\s+purchasers?|qualified\s+clients?"
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")
NAME = r"([A-Z][a-z]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][a-zA-Z'\-]+){1,2})"
CCO_PATS = [
    re.compile(NAME + r",?\s+(?:our\s+|the\s+firm'?s\s+)?(?:Chief\s+Compliance\s+Officer|CCO)\b"),
    re.compile(r"(?:Chief\s+Compliance\s+Officer|CCO),?\s+" + NAME),
]
EXEC_PAT = re.compile(
    NAME + r",?\s+(?:is\s+(?:our|the)\s+)?(?:Chief\s+Executive\s+Officer|CEO|President|Founder|Co-Founder|"
    r"Managing\s+(?:Partner|Director|Member|Principal)|Chief\s+Investment\s+Officer|CIO|Principal\s+Owner)\b"
)
BAD_NAME_WORDS = {"Chief", "Compliance", "Officer", "Firm", "Item", "Form", "Part", "Brochure", "Inc", "LLC",
                  "Investment", "Advisor", "Adviser", "Advisers", "Advisors", "Wealth", "Management", "Capital",
                  "Financial", "Group", "Partners", "The", "Our", "Securities", "Services", "Code", "Ethics",
                  "Please", "Contact", "Questions", "Fund", "Funds", "Trust", "Company", "Private", "Client",
                  "Executive", "Vice", "President", "Senior", "Service", "Fees", "Director", "Managing", "Officer",
                  "Bank", "Board", "Committee", "Department", "Supplement", "Additional", "Information"}
GENERIC_EMAIL = re.compile(r"^[^@]*(?:info|compliance|contact|service|admin|support|office|hello|operations|ops|"
                           r"question|inquir|mail|team|recon|data|legal|marketing|sales|help|client|invest|"
                           r"advisor|wealth|trading|general|privacy|hr)[^@]*@|^[^@]{1,3}@", re.I)
ACTION = re.compile(r"\b(?:we|our\s+(?:firm|advis[oe]rs?|clients?)|clients?|the\s+firm|[A-Z][A-Za-z]+)\b[^.]{0,160}?"
                    r"(?:recommend|allocat|invest|offer|access|make\s+available|participat|provide|select|include|utiliz|use)"
                    r"|venture\s+capital\s+(?:funds?|managers?|vehicles?|partnerships?|investments?|strateg|programs?)"
                    r"|asset\s+classes|portfolio\s+compan|co-?invest|direct\s+invest|growth\s+equity", re.I)
RISKY = re.compile(r"^\W*(?:[A-Za-z\s/,&-]{0,60}risks?\b|risk)|\bsubject\s+to\b|\bmay\s+be\s+(?:illiquid|in\s+the\s+early)", re.I)


def pdf_text(args):
    crd, vid = args
    out = f"{TXT}/{crd}/{vid}.txt"
    if os.path.exists(out):
        return
    src = f"{BRO}/{crd}/{vid}.pdf"
    if not os.path.exists(src):
        return
    os.makedirs(f"{TXT}/{crd}", exist_ok=True)
    try:
        r = PdfReader(src)
        pages = r.pages[:120]
        text = "\n".join((p.extract_text() or "") for p in pages)
    except Exception:
        text = ""
    with open(out, "w") as f:
        f.write(text)


def sentences_with(text, pat, n=3):
    hits = []
    for m in re.finditer(pat, text, re.I):
        s = text.rfind(".", 0, m.start()) + 1
        e = text.find(".", m.end())
        e = len(text) if e == -1 else e + 1
        snip = re.sub(r"\s+", " ", text[s:e]).strip()
        if len(snip) > 280:
            c = m.start() - s
            snip = "…" + snip[max(0, c - 120): c + 150] + "…"
        if snip and snip not in hits:
            hits.append(snip)
        if len(hits) >= n:
            break
    return hits


def clean_name(n):
    parts = n.split()
    if any(p.strip(".,") in BAD_NAME_WORDS for p in parts) or len(n) > 40:
        return None
    return n


def analyze(crd, texts):
    t = "\n".join(texts)
    low = t.lower()
    r = {"crd": crd, "brochure_chars": len(t)}
    vc = {k: len(re.findall(p, low)) for k, p in VC_PATTERNS.items()}
    pm = {k: len(re.findall(p, low)) for k, p in PM_PATTERNS.items()}
    pl = {k: len(re.findall(p, low)) for k, p in PLATFORMS.items()}
    r["vc_mentions"] = sum(vc.values())
    r["pm_mentions"] = sum(pm.values())
    r["vc_terms_found"] = "; ".join(f"{k} ({v})" for k, v in vc.items() if v)
    r["pm_terms_found"] = "; ".join(f"{k} ({v})" for k, v in pm.items() if v)
    r["alt_platforms_named"] = "; ".join(k for k, v in pl.items() if v)
    r["n_platforms"] = sum(1 for v in pl.values() if v)
    r["accredited_qp_mentions"] = len(re.findall(ACCRED, low))
    cu = {k: len(re.findall(p, low)) for k, p in CUSTODIANS.items()}
    named = sorted((k for k, v in cu.items() if v), key=lambda k: -cu[k])
    r["custodians_named"] = "; ".join(f"{k} ({cu[k]})" for k in named)
    core = [k for k in named if k not in ALT_CUSTODIANS and cu[k] >= 2]
    r["primary_custodian"] = core[0] if core else ""
    r["mentions_usvc"] = bool(pl["USVC"])
    vc_any = "|".join(VC_PATTERNS.values())
    vc_sents = sentences_with(t, vc_any, 200)
    active = [x for x in vc_sents if ACTION.search(x) and not RISKY.search(x)]
    r["vc_active_mentions"] = len(active)
    r["vc_evidence"] = " || ".join((active + [x for x in vc_sents if x not in active])[:3])
    r["pm_evidence"] = " || ".join(sentences_with(t, "|".join(
        [PM_PATTERNS[k] for k in ("interval fund", "private markets", "private equity", "alternative investments")]), 2))

    head = "\n".join(x[:6000] for x in texts)  # cover pages carry the contact block
    emails = [e.rstrip(".") for e in EMAIL.findall(t)]
    emails = [e for e in emails if not re.search(r"sec\.gov|finra\.org|adviserinfo|\.png|\.jpg", e, re.I)]
    ec = Counter(e.lower() for e in emails)
    personal = [e for e, _ in ec.most_common() if not GENERIC_EMAIL.match(e)]
    generic = [e for e, _ in ec.most_common() if GENERIC_EMAIL.match(e)]
    r["contact_emails"] = "; ".join(personal[:3])
    r["generic_emails"] = "; ".join(generic[:2])
    ph = Counter(PHONE.findall(head))
    r["brochure_phones"] = "; ".join(p for p, _ in ph.most_common(2))
    cco = Counter()
    for pat in CCO_PATS:
        for m in pat.finditer(t):
            n = clean_name(m.group(1))
            if n:
                cco[n] += 1
    r["cco_name"] = cco.most_common(1)[0][0] if cco else ""
    ex = Counter()
    for m in EXEC_PAT.finditer(t):
        n = clean_name(m.group(1))
        if n and n != r["cco_name"]:
            ex[n] += 1
    r["principals"] = "; ".join(n for n, _ in ex.most_common(3))
    return r


def tier(row):
    if not isinstance(row.get("brochure_status"), str):
        return "P - Brochure pending"
    if not row.get("brochure_chars"):
        return "X - No brochure text"
    if row["vc_active_mentions"] >= 2 or (row["vc_active_mentions"] >= 1 and (row["n_platforms"] or row["pm_mentions"] >= 10)):
        return "A - Venture explicit"
    if row["vc_mentions"] >= 1:
        return "B - Venture mentioned"
    if row["pm_mentions"] >= 5 or row["n_platforms"]:
        return "C - Private markets / alts"
    if row["pm_mentions"] >= 1:
        return "D - Alts mentioned (light)"
    return "E - No alts signal"


def score(row):
    s = 0.0
    s += min(row["vc_active_mentions"], 5) * 4.0                # 0-20 venture as something the firm does
    s += min(row["vc_mentions"], 10) * 1.0                      # 0-10 any venture language
    s += min(row["pm_mentions"], 25) * 0.6                      # 0-15 private markets depth
    s += min(row["n_platforms"], 2) * 5                         # 0-10 uses alt platforms
    s += 3 if row["accredited_qp_mentions"] else 0             # 0-3 serves accredited/QP
    s += 2 if row["any_vc_funds"] or row["any_pe_funds"] else 0
    aum = max(row["raum"], 1)
    s += max(0, min(15, 15 * (math.log10(aum) - math.log10(250e6)) / (math.log10(20e9) - math.log10(250e6))))
    s += 10 * min(1, max(0, row["hnw_share"] or 0) / 0.8)       # 0-10 HNW concentration
    avg = row["avg_account"] or 0
    s += 5 if avg >= 2e6 else 3 if avg >= 1e6 else 1 if avg >= 5e5 else 0
    s += 5 if row["raum"] and row["raum_discretionary"] / row["raum"] >= 0.8 else 0  # can allocate
    if row["is_broker_dealer_affiliated"]:
        s -= 5                                                  # centralized platform / gatekept
    if row["disciplinary_disclosure"]:
        s -= 3
    return round(max(0, min(100, s)), 1)


def main():
    idx = pd.read_csv("data/brochure_index.csv")
    ok = idx[idx["status"].isin(["ok", "cached"])]
    jobs = [(int(c), int(v)) for c, v in zip(ok["crd"], ok["brochure_version_id"])]
    with Pool(max(2, os.cpu_count() - 1)) as p:
        for i, _ in enumerate(p.imap_unordered(pdf_text, jobs, chunksize=8), 1):
            if i % 500 == 0:
                print(f"text {i}/{len(jobs)}", flush=True)

    by_firm = {}
    for c, v in jobs:
        f = f"{TXT}/{c}/{v}.txt"
        if os.path.exists(f):
            by_firm.setdefault(c, []).append(open(f).read())
    names = idx.groupby("crd").agg(
        brochure_names=("brochure_name", lambda x: " | ".join(map(str, x.dropna()))),
        brochure_date=("date_submitted", "first"),
        brochure_status=("status", lambda x: ",".join(sorted(set(x)))),
        brochure_version_ids=("brochure_version_id", lambda x: ",".join(str(int(v)) for v in x.dropna())),
    ).reset_index()

    mined = pd.DataFrame([analyze(c, t) for c, t in by_firm.items()])
    u = pd.read_csv("data/universe.csv")
    df = u.merge(names, on="crd", how="left").merge(mined, on="crd", how="left")
    for c in ("vc_mentions", "vc_active_mentions", "pm_mentions", "n_platforms", "accredited_qp_mentions"):
        df[c] = df[c].fillna(0).astype(int)
    df["tier"] = df.apply(tier, axis=1)
    df["lead_score"] = df.apply(score, axis=1)
    df["iapd_url"] = "https://adviserinfo.sec.gov/firm/summary/" + df["crd"].astype(str)
    df["brochure_url"] = df["brochure_version_ids"].fillna("").str.split(",").str[0].map(
        lambda v: f"https://files.adviserinfo.sec.gov/IAPD/Content/Common/crd_iapd_Brochure.aspx?BRCHR_VRSN_ID={v}" if v else "")
    df = df.sort_values(["lead_score"], ascending=False)
    df.to_csv("data/scored.csv", index=False)
    print(df["tier"].value_counts().sort_index())


if __name__ == "__main__":
    main()
