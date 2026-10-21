"""Fetch current Form ADV Part 2 brochure PDFs from IAPD for each firm in the universe.

Writes PDFs to data/brochures/<crd>/<versionId>.pdf and an index at
data/brochure_index.csv. Resumable: skips files already on disk.
"""
import csv
import json
import os
import ssl
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0"
API = "https://api.adviserinfo.sec.gov/search/firm/{crd}"
PDF = "https://files.adviserinfo.sec.gov/IAPD/Content/Common/crd_iapd_Brochure.aspx?BRCHR_VRSN_ID={vid}"
OUT_DIR = "data/brochures"
MAX_PER_FIRM = 4
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")


API_LOCK = threading.Lock()
API_INTERVAL = 2.5  # seconds between IAPD API calls (it 429s when hammered)
_last_api = [0.0]


def get(url, tries=6):
    is_api = url.startswith("https://api.")
    for i in range(tries):
        if is_api:
            with API_LOCK:
                wait = _last_api[0] + API_INTERVAL - time.time()
                if wait > 0:
                    time.sleep(wait)
                _last_api[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                ra = int(e.headers.get("Retry-After") or 0) or 60 * (i + 1)
                print(f"429: sleeping {ra}s", flush=True)
                with API_LOCK:
                    time.sleep(min(ra, 3600) + 5)
                continue
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def fetch_firm(crd):
    rows = []
    raw = get(API.format(crd=crd))
    if not raw:
        return [(crd, "", "", "", "api_error")]
    try:
        hits = json.loads(raw)["hits"]["hits"]
        content = json.loads(hits[0]["_source"]["iacontent"])
        details = (content.get("brochures") or {}).get("brochuredetails") or []
    except Exception:
        return [(crd, "", "", "", "parse_error")]
    if not details:
        return [(crd, "", "", "", "no_brochure")]
    details.sort(key=lambda d: time.strptime(d.get("dateSubmitted", "1/1/1900"), "%m/%d/%Y"), reverse=True)
    os.makedirs(f"{OUT_DIR}/{crd}", exist_ok=True)
    for d in details[:MAX_PER_FIRM]:
        vid = d["brochureVersionID"]
        path = f"{OUT_DIR}/{crd}/{vid}.pdf"
        status = "cached"
        if not os.path.exists(path) or os.path.getsize(path) < 1000:
            data = get(PDF.format(vid=vid))
            if data and data[:4] == b"%PDF":
                with open(path, "wb") as f:
                    f.write(data)
                status = "ok"
            else:
                status = "pdf_error"
        rows.append((crd, vid, d.get("brochureName", ""), d.get("dateSubmitted", ""), status))
    return rows


INDEX = "data/brochure_index.csv"


def main():
    with open("data/universe.csv") as f:
        crds = [int(r["crd"]) for r in csv.DictReader(f)]
    done = set()
    if os.path.exists(INDEX):
        with open(INDEX) as f:
            done = {int(r["crd"]) for r in csv.DictReader(f) if r["status"] not in ("api_error", "parse_error")}
    else:
        with open(INDEX, "w", newline="") as f:
            csv.writer(f).writerow(["crd", "brochure_version_id", "brochure_name", "date_submitted", "status"])
    todo = [c for c in crds if c not in done]
    print(f"{len(done)} done, {len(todo)} to fetch", flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex, open(INDEX, "a", newline="") as f:
        w = csv.writer(f)
        futs = {ex.submit(fetch_firm, c): c for c in todo}
        for i, fu in enumerate(as_completed(futs), 1):
            w.writerows(fu.result())
            f.flush()
            if i % 100 == 0:
                print(f"{time.strftime('%H:%M:%S')} {i}/{len(todo)} firms", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
