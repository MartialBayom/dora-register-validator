"""Look up the real LEIs (and ultimate parents) of common ICT third-party providers in the GLEIF register.

Data: GLEIF API, licence CC0. Each provider is searched by its legal name; the best ACTIVE match is kept.
"""
from pathlib import Path
import time

import pandas as pd
import requests
from rapidfuzz import fuzz

API = "https://api.gleif.org/api/v1"
OUT = Path(__file__).resolve().parents[1] / "data" / "ict_providers_gleif.csv"

PROVIDERS = [  # (legal name to search, service family used in the demo register)
    ("Microsoft Ireland Operations Limited", "cloud"),
    ("Amazon Web Services EMEA SARL|AMAZON WEB SERVICES EMEA SARL", "cloud"),
    ("Google Cloud EMEA Limited", "cloud"),
    ("Oracle Corporation", "software"),
    ("SAP SE", "software"),
    ("Salesforce, Inc.", "software"),
    ("International Business Machines Corporation", "infrastructure"),
    ("Kyndryl Holdings, Inc.", "infrastructure"),
    ("Equinix, Inc.", "data centre"),
    ("Bloomberg Finance L.P.", "market data"),
    ("Refinitiv Limited", "market data"),
    ("Society for Worldwide Interbank Financial Telecommunication|S.W.I.F.T. SC", "payments network"),
    ("Temenos AG", "core banking"),
    ("Avaloq Group AG", "core banking"),
    ("SimCorp A/S", "portfolio management"),
    ("Clearstream Banking S.A.", "custody platform"),
    ("Atos Group", "IT services"),
    ("Accenture public limited company|ACCENTURE PLC", "IT services"),
    ("Cisco Systems, Inc.", "network"),
    ("SERVICENOW, INC.|ServiceNow", "software"),
    ("LuxTrust S.A.", "trust services"),
    ("POST Luxembourg", "telecom"),
    ("Proximus Luxembourg S.A.", "telecom"),
    ("Fidelity National Information Services, Inc.", "software"),
    ("Broadridge Financial Solutions, Inc.", "software"),
]


def search(names: str) -> dict | None:
    """`names`: alternative spellings separated by |, tried in order."""
    for name in names.split("|"):
        hit = _search(name)
        if hit:
            return hit
    return None


def _search(name: str) -> dict | None:
    r = requests.get(f"{API}/lei-records", params={"filter[fulltext]": name, "page[size]": 25}, timeout=60)
    r.raise_for_status()
    best, best_score = None, 0
    for rec in r.json()["data"]:
        a = rec["attributes"]
        score = fuzz.token_sort_ratio(name.lower(), a["entity"]["legalName"]["name"].lower())
        if a["entity"]["status"] == "ACTIVE" and score > best_score:
            best, best_score = rec, score
    if not best or best_score < 85:
        return None
    a = best["attributes"]
    return {"lei": a["lei"], "legal_name": a["entity"]["legalName"]["name"],
            "country": a["entity"]["legalAddress"]["country"],
            "registration_status": a["registration"]["status"], "match_score": best_score}


def ultimate_parent(lei: str) -> tuple[str | None, str | None]:
    r = requests.get(f"{API}/lei-records/{lei}/ultimate-parent", timeout=60)
    if r.status_code != 200 or not r.json().get("data"):
        return None, None
    a = r.json()["data"]["attributes"]
    return a["lei"], latin_name(a["entity"])


def latin_name(entity: dict) -> str:
    """Prefer an English / Latin-script name when the legal name is in another script (e.g. Japanese)."""
    name = entity["legalName"]["name"]
    if name.isascii():
        return name
    for other in entity.get("otherNames", []) + entity.get("transliteratedOtherNames", []):
        if other["name"].isascii():
            return other["name"]
    return name


def main():
    rows = []
    for name, family in PROVIDERS:
        hit = search(name)
        name = name.split("|")[0]
        if hit is None:
            print(f"not found: {name}")
            continue
        hit["ultimate_parent_lei"], hit["ultimate_parent_name"] = ultimate_parent(hit["lei"])
        hit["service_family"] = family
        rows.append(hit)
        print(f"{hit['lei']}  {hit['legal_name']:55s} parent: {hit['ultimate_parent_name']}")
        time.sleep(0.2)
    OUT.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    lapsed = requests.get(f"{API}/lei-records", params={
        "filter[entity.legalAddress.country]": "LU", "filter[registration.status]": "LAPSED",
        "filter[entity.category]": "GENERAL", "page[size]": 30}, timeout=60).json()["data"]
    pd.DataFrame([{"lei": x["attributes"]["lei"], "legal_name": x["attributes"]["entity"]["legalName"]["name"],
                   "registration_status": "LAPSED"} for x in lapsed]).to_csv(OUT.with_name("lapsed_lu_leis.csv"),
                                                                            index=False)
    print(f"{len(rows)} providers saved")


if __name__ == "__main__":
    main()
