"""Turn the validator findings into an action list per owner, and (optionally) let Claude write it.

The findings themselves always come from the rule-based validator; the language model only rewrites
them for the people who must fix the data (vendor management, business owners, IT).
"""
import os

import pandas as pd

OWNER = {"B_01.01": "DORA reporting team", "B_02.01": "Procurement / vendor management",
         "B_02.02": "Procurement / vendor management", "B_05.01": "Vendor management",
         "B_06.01": "Business continuity / function owners", "B_07.01": "ICT risk management"}


def action_list(findings: pd.DataFrame, lang: str = "en") -> str:
    if findings.empty:
        return "No issue found." if lang == "en" else "Aucune anomalie détectée."
    lines = []
    for template, grp in findings.groupby("template"):
        owner = OWNER.get(template, "DORA reporting team")
        head = f"{owner} ({template}): {len(grp)} " + ("issue(s)" if lang == "en" else "anomalie(s)")
        lines.append(head)
        for (family, message), g in grp.groupby(["family", "message"]):
            rows = ", ".join(str(r + 1) for r in sorted(g["row"].unique())[:8])
            fix = g["suggested_fix"].replace("", pd.NA).dropna()
            tip = f" -> {fix.iloc[0]}" if len(fix) and g["rule"].iloc[0] != "LEI_FORMAT" else ""
            lines.append(f"  - [{family}] {message} (rows {rows}){tip}")
        for _, r in grp[grp["rule"] == "LEI_FORMAT"].iterrows():
            if r["suggested_fix"]:
                lines.append(f"      row {r['row'] + 1}: {r['value']} -> {r['suggested_fix']}")
    return "\n".join(lines)


def explain(findings: pd.DataFrame, lang: str = "en") -> tuple[str, str]:
    base = action_list(findings, lang)
    if findings.empty or not os.getenv("ANTHROPIC_API_KEY"):
        return base, "template"
    try:
        import anthropic

        language = "French" if lang == "fr" else "English"
        prompt = ("You help a Luxembourg bank fix its DORA Register of Information before submission to the CSSF. "
                  f"Write a short e-mail in {language} to the people who own the data, grouped by team, saying what "
                  "to fix first (blocking issues and critical functions first) and why it matters (the ESAs reject "
                  "registers with missing mandatory data). Use ONLY the findings below, do not invent any. "
                  f"Plain text.\n\nFINDINGS:\n{base}")
        msg = anthropic.Anthropic().messages.create(
            model=os.getenv("DORA_MODEL", "claude-haiku-4-5-20251001"), max_tokens=700,
            messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text.strip(), "claude"
    except Exception:
        return base, "template"
