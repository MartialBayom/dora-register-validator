"""LEI checks: ISO 17442 format and check digits, live status in GLEIF, and LEI suggestion by name."""
from pathlib import Path
import json
import re

import requests
from rapidfuzz import fuzz

API = "https://api.gleif.org/api/v1/lei-records"
CACHE = Path(__file__).resolve().parents[1] / "data" / "gleif_cache.json"
LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")


def check_digits_ok(lei: str) -> bool:
    if not isinstance(lei, str) or not LEI_RE.match(lei):
        return False
    return int("".join(str(int(c, 36)) for c in lei)) % 97 == 1


def make_lei(prefix18: str) -> str:
    """Build a LEI with valid check digits (ISO 7064 mod 97-10) from 18 characters."""
    base = prefix18.upper()
    n = int("".join(str(int(c, 36)) for c in base + "00"))
    return f"{base}{98 - n % 97:02d}"


class Gleif:
    """Batch lookup with a local cache, so the validator also works offline after a first run."""

    def __init__(self, offline: bool = False):
        self.offline = offline
        self.cache: dict = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    def lookup(self, leis) -> dict:
        leis = sorted({x for x in leis if check_digits_ok(x)})
        todo = [x for x in leis if x not in self.cache]
        if todo and not self.offline:
            for i in range(0, len(todo), 100):
                chunk = todo[i:i + 100]
                r = requests.get(API, params={"filter[lei]": ",".join(chunk), "page[size]": 200}, timeout=60)
                r.raise_for_status()
                found = {}
                for rec in r.json()["data"]:
                    a = rec["attributes"]
                    found[a["lei"]] = {"name": a["entity"]["legalName"]["name"], "entity_status": a["entity"]["status"],
                                       "registration_status": a["registration"]["status"],
                                       "country": a["entity"]["legalAddress"]["country"]}
                for lei in chunk:
                    self.cache[lei] = found.get(lei)          # None = not in GLEIF
            CACHE.write_text(json.dumps(self.cache, indent=1, ensure_ascii=False))
        return {x: self.cache.get(x, "unknown") for x in leis}

    def suggest(self, name: str, country: str | None = None) -> dict | None:
        """Find the most likely LEI for a provider name (used to propose a fix)."""
        key = f"suggest::{name}::{country}"
        if key in self.cache:
            return self.cache[key]
        if self.offline:
            return None
        params = {"filter[fulltext]": name, "page[size]": 20, "filter[entity.status]": "ACTIVE"}
        if country:
            params["filter[entity.legalAddress.country]"] = country
        best = None
        for rec in requests.get(API, params=params, timeout=60).json().get("data", []):
            a = rec["attributes"]
            score = fuzz.token_sort_ratio(name.lower(), a["entity"]["legalName"]["name"].lower())
            if a["registration"]["status"] == "ISSUED" and (best is None or score > best["score"]):
                best = {"lei": a["lei"], "name": a["entity"]["legalName"]["name"], "score": score}
        best = best if best and best["score"] >= 85 else None
        self.cache[key] = best
        CACHE.write_text(json.dumps(self.cache, indent=1, ensure_ascii=False))
        return best
