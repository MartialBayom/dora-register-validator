"""Inject the ESAs' dry-run error mix into the demo register, run the validator and measure detection.

Also measures the LEI auto-fix: for a mistyped provider LEI, does the GLEIF name search give back the right one?
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from generate import TEST_LEIS, build_clean, inject_errors
from lei import Gleif
from validator import concentration, quality_score, validate

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DRY_RUN_FAMILIES = {"missing", "lei_typo", "bad_value", "bad_date", "duplicate"}


def detected(truth_row, findings: pd.DataFrame) -> bool:
    f = findings[(findings["template"] == truth_row["template"]) & (findings["row"] == truth_row["row"])]
    if truth_row["error_type"] in ("duplicate", "critical_not_assessed"):
        return len(f) > 0
    return bool((f["column"].str.contains(truth_row["column"], regex=False)).any())


def main(runs: int = 10):
    REPORTS.mkdir(exist_ok=True)
    gleif = Gleif()
    clean = build_clean()
    baseline = validate(clean, gleif, TEST_LEIS)       # findings in the CLEAN register = real issues in GLEIF data
    baseline.to_csv(REPORTS / "findings_clean_register.csv", index=False)

    rows, fixes = [], []
    for seed in range(runs):
        dirty, truth = inject_errors(clean, n=120, seed=seed)
        findings = validate(dirty, gleif, TEST_LEIS)
        truth["detected"] = truth.apply(lambda r: detected(r, findings), axis=1)
        truth["seed"] = seed
        rows.append(truth)
        prov_clean = clean["B_05.01"]
        for _, f in findings[findings["rule"] == "LEI_FORMAT"].iterrows():
            if f["template"] == "B_05.01" and f["column"] == "provider_id":
                good = prov_clean.at[f["row"], "provider_id"]
                fixes.append(good in f["suggested_fix"])
        if seed == 0:
            dirty_findings = findings
            for t, df in dirty.items():
                df.to_csv(ROOT / "data" / f"demo_register_with_errors_{t}.csv", index=False)
            findings.to_csv(REPORTS / "findings_demo_register.csv", index=False)
            quality_score(dirty, findings).to_csv(REPORTS / "quality_by_template.csv", index=False)

    res = pd.concat(rows)
    res["in_dry_run_checks"] = res["error_type"].isin(DRY_RUN_FAMILIES)
    by_type = (res.groupby(["in_dry_run_checks", "error_type"])["detected"].agg(["count", "mean"])
               .rename(columns={"count": "injected", "mean": "detected_pct"}).reset_index())
    by_type["detected_pct"] = (100 * by_type["detected_pct"]).round(1)
    by_type.sort_values(["in_dry_run_checks", "injected"], ascending=False).to_csv(REPORTS / "detection_by_error_type.csv",
                                                                                  index=False)
    conc = concentration(clean)
    conc.to_csv(REPORTS / "concentration_critical_functions.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 3.6))
    top = conc.head(6).iloc[::-1]
    labels = top["group"].str.title().str.replace(r",? (Inc\.|Public Limited Company|Aktiengesellschaft)$", "", regex=True)
    ax.barh(labels, top["critical_functions"], color="#2C5F8A")
    ax.xaxis.get_major_locator().set_params(integer=True)
    ax.bar_label(ax.containers[0], padding=3)
    ax.set_title("Critical functions per provider group (ultimate parent from GLEIF)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, top["critical_functions"].max() + 1)
    plt.tight_layout()
    plt.savefig(REPORTS / "concentration.png", dpi=150)

    summary = {
        "runs": runs, "errors_injected": int(len(res)), "detected_pct": round(100 * res["detected"].mean(), 1),
        "lei_typo_autofix_pct": round(100 * sum(fixes) / len(fixes), 1) if fixes else None,
        "lei_typo_autofix_n": len(fixes),
        "findings_in_clean_register": baseline[["rule", "template", "column", "value", "message"]].to_dict("records"),
        "findings_demo_register": int(len(dirty_findings)),
    }
    (REPORTS / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(by_type.to_string())
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(conc.head(5).to_string())


if __name__ == "__main__":
    main()
