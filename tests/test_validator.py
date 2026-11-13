import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from generate import TEST_LEIS, build_clean, inject_errors  # noqa: E402
from lei import Gleif, check_digits_ok, make_lei  # noqa: E402
from validator import concentration, validate  # noqa: E402


@pytest.fixture(scope="module")
def gleif():
    return Gleif(offline=True)          # uses data/gleif_cache.json, no network in tests


@pytest.fixture(scope="module")
def clean():
    return build_clean()


def test_lei_check_digits():
    assert check_digits_ok("549300WCLFVEBTBNRF76")          # Microsoft Ireland Operations Ltd
    assert not check_digits_ok("549300WCLFVEBTBNRF77")
    assert not check_digits_ok("TOO-SHORT")
    assert check_digits_ok(make_lei("9845DEMO0BANKLUX00"))


def test_clean_register_only_has_real_gleif_findings(clean, gleif):
    f = validate(clean, gleif, TEST_LEIS)
    assert set(f["rule"]) <= {"LEI_STATUS"}               # e.g. a provider LEI that lapsed in GLEIF


@pytest.mark.parametrize("kind", ["missing", "lei_typo", "bad_value", "duplicate", "broken_ref",
                                  "end_before_start", "wrong_lei", "lapsed_lei"])
def test_each_error_type_is_caught(clean, gleif, kind):
    dirty, truth = inject_errors(clean, n=300, seed=1)
    findings = validate(dirty, gleif, TEST_LEIS)
    sub = truth[truth["error_type"] == kind]
    assert len(sub)
    hits = [((findings["template"] == r.template) & (findings["row"] == r.row)).any() for r in sub.itertuples()]
    assert sum(hits) / len(hits) >= 0.8


def test_missing_entity_lei_is_blocking(clean, gleif):
    reg = {t: df.copy() for t, df in clean.items()}
    reg["B_01.01"].at[0, "fe_lei"] = None
    f = validate(reg, gleif, TEST_LEIS)
    assert (f["severity"] == "Blocking").any()


def test_concentration_finds_microsoft(clean):
    top = concentration(clean).iloc[0]
    assert top["group"] == "MICROSOFT CORPORATION" and top["critical_functions"] >= 3
