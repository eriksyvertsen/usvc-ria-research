"""Build the wealth-channel RIA universe from the SEC monthly adviser file.

Filter: US main office, regulatory AUM >= $250M, and >= 40% of RAUM from
individual (5D(a)(3)) + high-net-worth (5D(b)(3)) clients.
"""
import sys
import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/sec_ia/ia09012026.csv"
OUT = "data/universe.csv"
AUM_FLOOR = 250e6
INDIV_SHARE = 0.40

df = pd.read_csv(SRC, encoding="latin-1", low_memory=False)


def num(c):
    return pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce").fillna(0)


df["raum"] = num("5F(2)(c)")
df["raum_discretionary"] = num("5F(2)(a)")
df["accounts"] = num("5F(2)(f)")
df["indiv_clients"] = num("5D(a)(1)")
df["hnw_clients"] = num("5D(b)(1)")
df["indiv_aum"] = num("5D(a)(3)")
df["hnw_aum"] = num("5D(b)(3)")
df["employees"] = num("5B(1)")
df["advisory_staff"] = num("5B(2)")
df["other_offices"] = num("Total number of offices, other than your Principal Office and place of business")
df["private_fund_gav"] = num("Total Gross Assets of Private Funds")
df["n_private_funds"] = num("Count of Private Funds - 7B(1)")
df["n_vc_funds"] = num("Total number of VC funds")
df["n_pe_funds"] = num("Total number of PE funds")

df["hnw_indiv_share"] = (df["indiv_aum"] + df["hnw_aum"]) / df["raum"].where(df["raum"] > 0)
df["hnw_share"] = df["hnw_aum"] / df["raum"].where(df["raum"] > 0)
df["avg_account"] = df["raum"] / df["accounts"].where(df["accounts"] > 0)

m = (
    (df["Main Office Country"] == "United States")
    & (df["raum"] >= AUM_FLOOR)
    & (df["hnw_indiv_share"] >= INDIV_SHARE)
)
u = df[m].copy()

yn = lambda c: u[c].fillna("N").eq("Y")
u["is_broker_dealer_affiliated"] = yn("6A(1)") | yn("7A(1)")
u["is_insurance_affiliated"] = yn("6A(7)") | yn("7A(8)") if "7A(8)" in u else yn("6A(7)")
u["sponsors_wrap"] = yn("5I(1)")
u["financial_planning"] = yn("5G(1)") if "5G(1)" in u else False
u["advises_private_funds"] = yn("7B")
u["any_vc_funds"] = yn("Any VC Funds")
u["any_pe_funds"] = yn("Any PE Funds")
u["recommends_securities_with_interest"] = yn("8A(3)") | yn("8C(1)")
u["disciplinary_disclosure"] = yn("11")

keep = {
    "Organization CRD#": "crd",
    "SEC#": "sec_number",
    "Primary Business Name": "firm_name",
    "Legal Name": "legal_name",
    "Main Office Street Address 1": "address1",
    "Main Office Street Address 2": "address2",
    "Main Office City": "city",
    "Main Office State": "state",
    "Main Office Postal Code": "zip",
    "Main Office Telephone Number": "main_phone",
    "Website Address": "website",
    "Latest ADV Filing Date": "latest_adv_filing",
    "3A": "org_form",
}
cols = list(keep) + [
    "raum", "raum_discretionary", "accounts", "avg_account", "indiv_clients", "hnw_clients",
    "indiv_aum", "hnw_aum", "hnw_indiv_share", "hnw_share", "employees", "advisory_staff",
    "other_offices", "is_broker_dealer_affiliated", "is_insurance_affiliated", "sponsors_wrap",
    "advises_private_funds", "n_private_funds", "n_vc_funds", "n_pe_funds", "private_fund_gav",
    "any_vc_funds", "any_pe_funds", "recommends_securities_with_interest", "disciplinary_disclosure",
]
u = u[cols].rename(columns=keep)
u["crd"] = u["crd"].astype(int)
u = u.sort_values("raum", ascending=False)
u.to_csv(OUT, index=False)
print(f"{len(u)} firms -> {OUT}")
