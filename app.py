"""Streamlit demo: run `streamlit run app.py`."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
from explain import explain  # noqa: E402
from generate import TEST_LEIS, build_clean, inject_errors  # noqa: E402
from lei import Gleif  # noqa: E402
from model import TEMPLATES  # noqa: E402
from validator import concentration, quality_score, validate  # noqa: E402

ROOT = Path(__file__).parent
st.set_page_config(page_title="DORA Register of Information validator", page_icon="🛡️", layout="wide")
st.title("DORA Register of Information validator")
st.caption("Fictional Luxembourg banking group, REAL ICT providers (LEIs and parent groups from GLEIF).")

c1, c2, c3 = st.columns(3)
n_errors = c1.slider("Errors to inject (dry-run mix)", 0, 200, 60)
seed = c2.number_input("Seed", 0, 999, 0)
lang = c3.radio("Language", ["en", "fr"], horizontal=True)
offline = st.toggle("Offline mode (use the GLEIF cache only)", value=False)

clean = build_clean()
register, truth = inject_errors(clean, n=n_errors, seed=int(seed)) if n_errors else (clean, pd.DataFrame())
findings = validate(register, Gleif(offline=offline), TEST_LEIS)

m1, m2, m3 = st.columns(3)
m1.metric("Findings", len(findings))
m2.metric("Blocking", int((findings["severity"] == "Blocking").sum()))
m3.metric("Errors injected", len(truth))

tab1, tab2, tab3, tab4 = st.tabs(["Findings", "Action list", "Concentration risk", "Register"])
with tab1:
    st.dataframe(quality_score(register, findings), hide_index=True)
    fam = st.multiselect("Family", sorted(findings["family"].unique()), default=sorted(findings["family"].unique()))
    st.dataframe(findings[findings["family"].isin(fam)], hide_index=True)
    st.download_button("Download findings (CSV)", findings.to_csv(index=False), "dora_findings.csv")
with tab2:
    text, source = explain(findings, lang)
    st.caption(f"Written by: {source}")
    st.text(text)
with tab3:
    st.write("Which provider groups support several critical or important functions?")
    st.dataframe(concentration(register), hide_index=True)
with tab4:
    t = st.selectbox("Template", list(TEMPLATES), format_func=lambda x: f"{x} - {TEMPLATES[x]}")
    st.dataframe(register[t])
