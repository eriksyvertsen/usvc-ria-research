"""Re-score whatever brochures are on disk and upsert every firm into Supabase.

Safe to run repeatedly while 02_fetch_brochures.py is still downloading: firms
without a brochure yet land as tier "P - Brochure pending" and get overwritten
on later runs.

Reads SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY from .env.local.
"""
import json
import math
import os
import ssl
import subprocess
import sys
import urllib.request

import pandas as pd

CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
INT_COLS = {"crd", "accounts", "n_private_funds", "brochure_chars", "vc_mentions", "vc_active_mentions",
            "pm_mentions", "n_platforms", "accredited_qp_mentions"}
BOOL_COLS = {"is_broker_dealer_affiliated", "is_insurance_affiliated", "sponsors_wrap", "advises_private_funds",
             "any_vc_funds", "any_pe_funds", "recommends_securities_with_interest", "disciplinary_disclosure",
             "mentions_usvc"}


def load_env():
    for line in open(".env.local"):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)


def post(path, rows, prefer):
    url = os.environ["SUPABASE_URL"] + "/rest/v1/" + path
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    req = urllib.request.Request(url, data=json.dumps(rows).encode(), method="POST", headers={
        "apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": prefer})
    with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
        return r.status


def clean(v, col):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if col in INT_COLS:
        return int(v)
    if col in BOOL_COLS:
        return bool(v) if not isinstance(v, str) else v.lower() == "true"
    if isinstance(v, float):
        return v
    return str(v)


def main():
    load_env()
    subprocess.run([sys.executable, "-I", "scripts/03_extract_and_score.py"], check=True)  # writes data/scored.csv

    df = pd.read_csv("data/scored.csv", low_memory=False)
    rows = [{c: clean(v, c) for c, v in r.items()} for r in df.to_dict("records")]
    now = pd.Timestamp.utcnow().isoformat()
    for r in rows:
        r["updated_at"] = now
    for i in range(0, len(rows), 500):
        post("firms?on_conflict=crd", rows[i:i + 500], "resolution=merge-duplicates,return=minimal")

    idx = pd.read_csv("data/brochure_index.csv")
    pending = int((df["tier"] == "P - Brochure pending").sum())
    post("pipeline_runs", [{
        "firms_total": len(df),
        "firms_with_brochure": int(df["brochure_chars"].fillna(0).gt(0).sum()),
        "firms_pending": pending,
        "brochures_downloaded": int(idx["status"].isin(["ok", "cached"]).sum()),
        "note": "fetch in progress" if pending else "complete",
    }], "return=minimal")
    print(f"synced {len(rows)} firms to Supabase ({pending} pending)", flush=True)


if __name__ == "__main__":
    main()
