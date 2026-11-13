"""Build a demo Register of Information for a FICTIONAL Luxembourg banking group, using REAL ICT providers
(LEIs and ultimate parents from GLEIF), then inject the error types seen in the ESAs' 2024 dry run.
"""
from pathlib import Path
import random

import pandas as pd

from lei import make_lei

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# fictional entities: valid LEI format, not registered in GLEIF (declared as test LEIs)
GROUP = {"Demo Bank Luxembourg S.A.": make_lei("9845DEMO0BANKLUX00"),
         "Demo Asset Management S.A.": make_lei("9845DEMO0AMLUX0000"),
         "Demo Payments S.A.": make_lei("9845DEMO0PAYLUX000")}
TEST_LEIS = set(GROUP.values())

FUNCTIONS = [  # (id, name, critical, entity)
    ("F01", "Payments execution", True, "Demo Payments S.A."),
    ("F02", "Core banking - accounts and deposits", True, "Demo Bank Luxembourg S.A."),
    ("F03", "Custody and settlement", True, "Demo Bank Luxembourg S.A."),
    ("F04", "Portfolio management", True, "Demo Asset Management S.A."),
    ("F05", "Client onboarding and KYC", True, "Demo Bank Luxembourg S.A."),
    ("F06", "AML transaction monitoring", True, "Demo Bank Luxembourg S.A."),
    ("F07", "Regulatory reporting", True, "Demo Bank Luxembourg S.A."),
    ("F08", "Market data and pricing", True, "Demo Asset Management S.A."),
    ("F09", "Cybersecurity monitoring", True, "Demo Bank Luxembourg S.A."),
    ("F10", "E-mail and collaboration", False, "Demo Bank Luxembourg S.A."),
    ("F11", "Customer relationship management", False, "Demo Bank Luxembourg S.A."),
    ("F12", "Data warehouse and BI", False, "Demo Bank Luxembourg S.A."),
    ("F13", "HR and payroll", False, "Demo Bank Luxembourg S.A."),
    ("F14", "Strong customer authentication", True, "Demo Payments S.A."),
]

SERVICES = [  # (provider legal name in GLEIF, function, ICT service type, sensitiveness, reliance, substitutability)
    ("MICROSOFT IRELAND OPERATIONS LIMITED", "F10", "S19", "Medium", "Material reliance", "Medium complexity in terms of substitutability"),
    ("MICROSOFT IRELAND OPERATIONS LIMITED", "F12", "S17", "High", "Material reliance", "Highly complex substitutability"),
    ("MICROSOFT IRELAND OPERATIONS LIMITED", "F06", "S18", "High", "Full reliance", "Highly complex substitutability"),
    ("MICROSOFT IRELAND OPERATIONS LIMITED", "F09", "S04", "High", "Material reliance", "Highly complex substitutability"),
    ("MICROSOFT IRELAND OPERATIONS LIMITED", "F05", "S17", "High", "Material reliance", "Highly complex substitutability"),
    ("GOOGLE CLOUD EMEA LIMITED", "F12", "S06", "Medium", "Low reliance", "Easily substitutable"),
    ("ORACLE CORPORATION", "F07", "S13", "High", "Material reliance", "Highly complex substitutability"),
    ("SAP SE", "F13", "S19", "High", "Material reliance", "Medium complexity in terms of substitutability"),
    ("SALESFORCE, INC.", "F11", "S19", "Medium", "Material reliance", "Medium complexity in terms of substitutability"),
    ("INTERNATIONAL BUSINESS MACHINES CORPORATION", "F07", "S15", "Medium", "Low reliance", "Easily substitutable"),
    ("KYNDRYL HOLDINGS, INC.", "F02", "S14", "High", "Material reliance", "Highly complex substitutability"),
    ("EQUINIX, INC.", "F02", "S07", "High", "Full reliance", "Highly complex substitutability"),
    ("EQUINIX, INC.", "F01", "S07", "High", "Full reliance", "Highly complex substitutability"),
    ("Bloomberg Finance L.P.", "F08", "S05", "Low", "Full reliance", "Not substitutable"),
    ("REFINITIV LIMITED", "F08", "S05", "Low", "Material reliance", "Medium complexity in terms of substitutability"),
    ("SOCIETY FOR WORLDWIDE INTERBANK FINANCIAL TELECOMMUNICATION", "F01", "S11", "High", "Full reliance", "Not substitutable"),
    ("TEMENOS AG", "F02", "S13", "High", "Full reliance", "Not substitutable"),
    ("Avaloq Group AG", "F03", "S19", "High", "Full reliance", "Highly complex substitutability"),
    ("SIMCORP A/S", "F04", "S19", "High", "Full reliance", "Highly complex substitutability"),
    ("CLEARSTREAM BANKING S.A.", "F03", "S19", "High", "Full reliance", "Not substitutable"),
    ("Atos Group", "F09", "S04", "High", "Material reliance", "Medium complexity in terms of substitutability"),
    ("ACCENTURE PUBLIC LIMITED COMPANY", "F05", "S02", "Medium", "Low reliance", "Easily substitutable"),
    ("CISCO SYSTEMS, INC.", "F01", "S12", "Low", "Low reliance", "Medium complexity in terms of substitutability"),
    ("CISCO SYSTEMS, INC.", "F02", "S12", "Low", "Low reliance", "Medium complexity in terms of substitutability"),
    ("LuxTrust S.A.", "F14", "S04", "High", "Full reliance", "Highly complex substitutability"),
    ("POST LUXEMBOURG", "F01", "S10", "Medium", "Material reliance", "Medium complexity in terms of substitutability"),
    ("PROXIMUS LUXEMBOURG S.A.", "F02", "S10", "Medium", "Material reliance", "Medium complexity in terms of substitutability"),
    ("FIDELITY NATIONAL INFORMATION SERVICES, INC.", "F04", "S13", "High", "Material reliance", "Highly complex substitutability"),
    ("BROADRIDGE FINANCIAL SOLUTIONS, INC.", "F07", "S19", "High", "Material reliance", "Medium complexity in terms of substitutability"),
]


def build_clean(seed: int = 3) -> dict[str, pd.DataFrame]:
    rng = random.Random(seed)
    prov = pd.read_csv(DATA / "ict_providers_gleif.csv")
    prov = prov[prov["legal_name"].isin({s[0] for s in SERVICES})].drop_duplicates("lei")
    b0101 = pd.DataFrame([{"fe_lei": GROUP["Demo Bank Luxembourg S.A."], "fe_name": "Demo Bank Luxembourg S.A.",
                           "country": "LU", "entity_type": "Credit institution", "competent_authority": "CSSF",
                           "reporting_date": "2026-12-31"}])
    b0501 = pd.DataFrame({
        "provider_id": prov["lei"], "provider_id_type": "LEI", "provider_name": prov["legal_name"],
        "person_type": "Legal person", "hq_country": prov["country"],
        "currency": "EUR", "annual_expense": [rng.randint(20, 900) * 1000 for _ in range(len(prov))],
        "ultimate_parent_id": prov["ultimate_parent_lei"], "ultimate_parent_name": prov["ultimate_parent_name"],
    }).reset_index(drop=True)
    lei_of = dict(zip(prov["legal_name"], prov["lei"]))
    country_of = dict(zip(prov["legal_name"], prov["country"]))
    fun = pd.DataFrame([{"function_id": fid, "function_name": n, "fe_lei": GROUP[ent],
                         "criticality": "Critical or important" if crit else "Not critical or important",
                         "last_assessment_date": f"2026-{rng.randint(1, 11):02d}-{rng.randint(1, 28):02d}",
                         "rto_hours": rng.choice([2, 4, 8, 24]) if crit else 72,
                         "rpo_hours": rng.choice([0, 1, 4]) if crit else 24} for fid, n, crit, ent in FUNCTIONS])
    ent_of = {fid: GROUP[ent] for fid, _, _, ent in FUNCTIONS}
    critical = {fid for fid, _, crit, _ in FUNCTIONS if crit}
    c201, c202, c701 = [], [], []
    for k, (pname, fid, stype, sens, rel, subst) in enumerate(SERVICES, start=1):
        ref = f"CTR-{2019 + k % 7}-{k:04d}"
        start = f"{2019 + k % 7}-{rng.randint(1, 12):02d}-01"
        end = f"{2028 + k % 4}-12-31"
        c201.append({"contract_ref": ref, "arrangement_type": "Standalone arrangement", "currency": "EUR",
                     "annual_expense": rng.randint(10, 600) * 1000})
        c202.append({"contract_ref": ref, "fe_lei": ent_of[fid], "provider_id": lei_of[pname],
                     "provider_id_type": "LEI", "function_id": fid, "ict_service_type": stype,
                     "start_date": start, "end_date": end, "governing_law_country": "LU",
                     "service_country": country_of[pname] if country_of[pname] in ("LU", "IE", "DE", "FR", "BE") else "IE",
                     "data_storage": "Yes" if stype in ("S07", "S09", "S17", "S18", "S19") else "No",
                     "data_sensitiveness": sens, "reliance_level": rel})
        if fid in critical:
            c701.append({"contract_ref": ref, "provider_id": lei_of[pname], "ict_service_type": stype,
                         "substitutability": subst, "last_audit_date": f"2026-{rng.randint(1, 10):02d}-15",
                         "exit_plan": "No" if subst == "Not substitutable" and rng.random() < 0.5 else "Yes",
                         "reintegration_possible": "Highly complex" if "complex" in subst.lower() else "Difficult",
                         "alternative_providers": "No" if subst == "Not substitutable" else "Yes"})
    return {"B_01.01": b0101, "B_02.01": pd.DataFrame(c201), "B_02.02": pd.DataFrame(c202), "B_05.01": b0501,
            "B_06.01": fun, "B_07.01": pd.DataFrame(c701)}


def _typo_lei(lei: str, rng: random.Random) -> str:
    i = rng.randint(4, 17)
    c = rng.choice([x for x in "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789" if x != lei[i]])
    return lei[:i] + c + lei[i + 1:]


def inject_errors(reg: dict[str, pd.DataFrame], n: int = 120, seed: int = 9):
    """Inject errors with the dry-run mix (86% missing, 6.5% LEI, 4% list values, ~3% keys/dates)
    plus error types the dry run did not test. Returns (dirty register, ground truth)."""
    rng = random.Random(seed)
    reg = {t: df.copy().astype(object) for t, df in reg.items()}
    truth = []
    lapsed = pd.read_csv(DATA / "lapsed_lu_leis.csv")["lei"].tolist()
    mix = (["missing"] * 86 + ["lei_typo"] * 6 + ["bad_value"] * 4 + ["bad_date"] * 2 + ["duplicate"] * 1
           + ["lapsed_lei"] * 2 + ["wrong_lei"] * 2 + ["broken_ref"] * 2 + ["end_before_start"] * 2
           + ["critical_not_assessed"] * 2)
    from model import ALLOWED, KEYS, MANDATORY
    used = set()
    for _ in range(n):
        kind = rng.choice(mix)
        if kind == "missing":
            t = rng.choice(["B_02.02", "B_05.01", "B_06.01", "B_07.01", "B_02.01"])
            col = rng.choice([c for c in MANDATORY[t] if c not in KEYS[t]])
            i = rng.choice(list(reg[t].index))
            if (t, i, col) in used:
                continue
            reg[t].at[i, col] = None
        elif kind == "lei_typo":
            t, col = "B_05.01", "provider_id"
            i = rng.choice(list(reg[t].index))
            if (t, i, col) in used or reg[t].at[i, col] is None:
                continue
            reg[t].at[i, col] = _typo_lei(reg[t].at[i, col], rng)
        elif kind == "lapsed_lei":
            t, col = "B_05.01", "ultimate_parent_id"
            i = rng.choice(list(reg[t].index))
            reg[t].at[i, col] = rng.choice(lapsed)
        elif kind == "wrong_lei":
            t, col = "B_05.01", "provider_id"
            i, j = rng.sample(list(reg[t].index), 2)
            if (t, i, col) in used:
                continue
            reg[t].at[i, col] = reg[t].at[j, "provider_id"]
            kind = "wrong_lei"   # also creates a duplicate key in B_05.01, by nature
        elif kind == "bad_value":
            (t, col), allowed = rng.choice([(k, v) for k, v in ALLOWED.items() if k[0] in reg and len(v) < 10])
            i = rng.choice(list(reg[t].index))
            if (t, i, col) in used or reg[t].at[i, col] is None:
                continue
            reg[t].at[i, col] = str(reg[t].at[i, col]).lower().replace(" ", "_")
        elif kind == "bad_date":
            t, col = rng.choice([("B_02.02", "start_date"), ("B_06.01", "last_assessment_date")])
            i = rng.choice(list(reg[t].index))
            v = reg[t].at[i, col]
            if v is None:
                continue
            y, m, d = str(v).split("-")
            reg[t].at[i, col] = f"{d}/{m}/{y}"          # European format instead of ISO
        elif kind == "duplicate":
            t = "B_02.01"
            i = rng.choice(list(reg[t].index))
            reg[t] = pd.concat([reg[t], reg[t].iloc[[i]]], ignore_index=True)
            i, col = len(reg[t]) - 1, "contract_ref"
        elif kind == "broken_ref":
            t, col = "B_02.02", "function_id"
            i = rng.choice(list(reg[t].index))
            reg[t].at[i, col] = "F99"
        elif kind == "end_before_start":
            t, col = "B_02.02", "end_date"
            i = rng.choice(list(reg[t].index))
            reg[t].at[i, col] = "2018-12-31"
        else:  # critical_not_assessed: delete a B_07.01 row
            t, col = "B_07.01", "contract_ref"
            if len(reg[t]) < 2:
                continue
            free = [x for x in reg[t].index if not any(u[0] == t and u[1] == x for u in used)]
            if not free:
                continue
            i = rng.choice(free)
            ref = reg[t].at[i, "contract_ref"]
            reg[t] = reg[t].drop(index=i)          # keep row numbers so the answer key stays valid
            t, i = "B_02.02", int(reg["B_02.02"].index[reg["B_02.02"]["contract_ref"] == ref][0])
        used.add((t, i, col))
        truth.append({"error_type": kind, "template": t, "row": i, "column": col})
    return reg, pd.DataFrame(truth)
