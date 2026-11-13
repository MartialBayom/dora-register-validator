"""Validate a DORA Register of Information before it is sent to the CSSF / ESAs.

Check families follow the ESAs' 2024 dry-run data quality checks (unique keys, LEI validity against GLEIF,
drop-down values, mandatory fields, dates), plus checks the dry run did not cover:
cross-template consistency, LEI name / status consistency, and concentration risk on critical functions.
"""
from dataclasses import dataclass

import pandas as pd
from rapidfuzz import fuzz

from lei import Gleif, check_digits_ok
from model import ALLOWED, DATE_COLUMNS, KEYS, LEI_COLUMNS, MANDATORY

BLOCKING = "Blocking"
WARNING = "Warning"


@dataclass
class Finding:
    rule: str
    family: str
    severity: str
    template: str
    row: int
    column: str
    value: str
    message: str
    suggested_fix: str = ""


def _empty(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and not v.strip())


def validate(register: dict[str, pd.DataFrame], gleif: Gleif | None = None,
             known_test_leis: set[str] = frozenset()) -> pd.DataFrame:
    gleif = gleif or Gleif()
    f: list[Finding] = []
    reporting_date = pd.to_datetime(register["B_01.01"]["reporting_date"].iloc[0], format="%Y-%m-%d", errors="coerce")

    for t, df in register.items():
        # 1. mandatory fields (B_01.01 is blocking, as in the dry run)
        for col in MANDATORY.get(t, []):
            for i, v in df[col].items():
                if _empty(v):
                    f.append(Finding("MAND", "Mandatory field", BLOCKING if t == "B_01.01" else WARNING, t, i, col,
                                     "", f"{col} is mandatory and empty"))
        # 2. unique keys
        keys = KEYS[t]
        dup = df[df.duplicated(keys, keep="first") & df[keys].notna().all(axis=1)]
        for i, r in dup.iterrows():
            f.append(Finding("KEY", "Unique identifier", WARNING, t, i, "+".join(keys),
                             " | ".join(str(r[k]) for k in keys), "duplicate key: the row cannot be linked",
                             "merge or delete the duplicate row"))
        # 3. drop-down values
        for (tt, col), allowed in ALLOWED.items():
            if tt != t:
                continue
            for i, v in df[col].items():
                if not _empty(v) and v not in allowed:
                    close = max(allowed, key=lambda a: fuzz.ratio(str(v).lower(), a.lower()))
                    f.append(Finding("LIST", "Drop-down value", WARNING, t, i, col, str(v),
                                     "value not in the allowed list", f"did you mean '{close}'?"))
        # 4. dates
        for col in DATE_COLUMNS.get(t, []):
            for i, v in df[col].items():
                if not _empty(v) and pd.isna(pd.to_datetime(v, format="%Y-%m-%d", errors="coerce")):
                    f.append(Finding("DATE", "Date", WARNING, t, i, col, str(v), "not a valid ISO date (YYYY-MM-DD)"))

    # 5. LEI: format, existence and status in GLEIF, name consistency
    all_leis = {v for t, cols in LEI_COLUMNS.items() for c in cols for v in register[t][c].dropna()}
    status = gleif.lookup(all_leis - set(known_test_leis))
    prov = register["B_05.01"]
    for t, cols in LEI_COLUMNS.items():
        df = register[t]
        for col in cols:
            for i, v in df[col].items():
                if _empty(v) or v in known_test_leis:
                    continue
                if t == "B_05.01" and col == "provider_id" and df.at[i, "provider_id_type"] != "LEI":
                    continue
                if not check_digits_ok(v):
                    fix = ""
                    if t == "B_05.01":
                        name = df.at[i, "provider_name"]
                        s = None if _empty(name) else gleif.suggest(name)
                        fix = f"GLEIF suggests {s['lei']} ({s['name']})" if s else "ask the provider for its LEI"
                    f.append(Finding("LEI_FORMAT", "LEI validity", WARNING, t, i, col, v,
                                     "invalid LEI (format or check digits, ISO 17442)", fix))
                    continue
                rec = status.get(v)
                if rec is None:
                    f.append(Finding("LEI_GLEIF", "LEI validity", WARNING, t, i, col, v, "LEI not found in GLEIF"))
                elif rec != "unknown":
                    if rec["registration_status"] in ("LAPSED", "RETIRED", "ANNULLED") or rec["entity_status"] != "ACTIVE":
                        f.append(Finding("LEI_STATUS", "LEI validity", WARNING, t, i, col, v,
                                         f"LEI registration is {rec['registration_status']} in GLEIF",
                                         "ask the entity to renew its LEI"))
                    if t == "B_05.01" and col == "provider_id" and not _empty(df.at[i, "provider_name"]):
                        score = fuzz.token_sort_ratio(str(df.at[i, "provider_name"]).lower(), rec["name"].lower())
                        if score < 80:
                            f.append(Finding("LEI_NAME", "Cross-check", WARNING, t, i, col, v,
                                             f"LEI belongs to '{rec['name']}', not to '{df.at[i, 'provider_name']}'",
                                             "check that the right LEI was copied"))

    # 6. cross-template consistency (not covered by the dry run)
    c201, c202, c701 = register["B_02.01"], register["B_02.02"], register["B_07.01"]
    fun = register["B_06.01"]
    ref_checks = [("B_02.02", "contract_ref", set(c201["contract_ref"]), "B_02.01"),
                  ("B_02.02", "provider_id", set(prov["provider_id"]), "B_05.01"),
                  ("B_02.02", "function_id", set(fun["function_id"]), "B_06.01"),
                  ("B_07.01", "contract_ref", set(c201["contract_ref"]), "B_02.01")]
    for t, col, ref, target in ref_checks:
        for i, v in register[t][col].items():
            if not _empty(v) and v not in ref:
                # root cause: often the SAME id was mistyped in the target template (one character away)
                near = [x for x in ref if isinstance(x, str) and len(x) == len(str(v))
                        and sum(a != b for a, b in zip(x, str(v))) == 1]
                hint = f"probably the typo '{near[0]}' in {target}: fix it there" if near else ""
                f.append(Finding("XREF", "Cross-template", WARNING, t, i, col, str(v), f"not found in {target}", hint))
    for i, r in c202.iterrows():
        s = pd.to_datetime(r["start_date"], format="%Y-%m-%d", errors="coerce")
        e = pd.to_datetime(r["end_date"], format="%Y-%m-%d", errors="coerce")
        if pd.notna(s) and pd.notna(e) and e < s:
            f.append(Finding("DATE_ORDER", "Date", WARNING, "B_02.02", i, "end_date", r["end_date"],
                             "end date before start date"))
    for i, v in fun["last_assessment_date"].items():
        d = pd.to_datetime(v, format="%Y-%m-%d", errors="coerce")
        if pd.notna(d) and pd.notna(reporting_date) and d > reporting_date:
            f.append(Finding("DATE_FUTURE", "Date", WARNING, "B_06.01", i, "last_assessment_date", v,
                             "assessment date after the reporting date"))
    critical = set(fun.loc[fun["criticality"] == "Critical or important", "function_id"])
    assessed = set(zip(c701["contract_ref"], c701["ict_service_type"]))
    for i, r in c202[c202["function_id"].isin(critical)].iterrows():
        if (r["contract_ref"], r["ict_service_type"]) not in assessed:
            f.append(Finding("CRIT_ASSESS", "Cross-template", WARNING, "B_02.02", i, "contract_ref",
                             r["contract_ref"], "service supports a critical function but has no B_07.01 assessment"))

    out = pd.DataFrame([x.__dict__ for x in f])
    return out if len(out) else pd.DataFrame(columns=list(Finding.__dataclass_fields__))


def concentration(register: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Critical functions per ultimate provider group: where one group failing stops several critical functions."""
    fun, c202, prov = register["B_06.01"], register["B_02.02"], register["B_05.01"]
    crit = fun[fun["criticality"] == "Critical or important"][["function_id", "function_name"]].drop_duplicates()
    m = c202.merge(crit, on="function_id").merge(prov[["provider_id", "provider_name", "ultimate_parent_name"]],
                                                  on="provider_id", how="left")
    m["group"] = m["ultimate_parent_name"].fillna(m["provider_name"])
    a7 = register["B_07.01"][["contract_ref", "ict_service_type", "exit_plan", "substitutability"]]
    m = m.merge(a7, on=["contract_ref", "ict_service_type"], how="left")
    g = m.groupby("group").agg(critical_functions=("function_id", "nunique"),
                               functions=("function_name", lambda s: ", ".join(sorted(set(s.dropna())))),
                               without_exit_plan=("exit_plan", lambda s: int((s != "Yes").sum())),
                               not_substitutable=("substitutability", lambda s: int((s == "Not substitutable").sum())))
    g["share_of_critical_functions_pct"] = (100 * g["critical_functions"] / max(len(crit), 1)).round(1)
    return g.sort_values("critical_functions", ascending=False).reset_index()


def quality_score(register: dict[str, pd.DataFrame], findings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t, df in register.items():
        cells = df.size
        bad = findings[findings["template"] == t][["row", "column"]].drop_duplicates()
        rows.append({"template": t, "rows": len(df), "findings": int((findings["template"] == t).sum()),
                     "cells_ok_pct": round(100 * (1 - len(bad) / cells), 2) if cells else 100.0})
    return pd.DataFrame(rows)
