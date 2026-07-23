"""Deterministic rule tests for the HK corridor egress demo."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from checker.explain import _render_user_prompt, explain_findings
from checker.ifc_adapter import extract_doors_from_ifc, merge_ifc_doors_into_model
from checker.rules import run_checks

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FAIL_SAMPLE = DATA / "sample_hk_tower_floor.json"
PASS_SAMPLE = DATA / "sample_hk_tower_floor_compliant.json"
IFC_SAMPLE = DATA / "sample_hk_tower_floor.ifc"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fail_sample_has_three_fails():
    result = run_checks(_load(FAIL_SAMPLE))
    assert result.summary["fail"] == 3
    assert result.summary["pass"] == 2
    fail_ids = {f.element_id for f in result.findings if f.severity == "fail"}
    assert fail_ids == {"D-STAIR-B", "F-STROLLER-01", "F-CARTON-01"}


def test_compliant_sample_has_zero_fails():
    result = run_checks(_load(PASS_SAMPLE))
    assert result.summary["fail"] == 0
    assert result.summary["pass"] == 4


def test_rule_config_threshold_is_honoured():
    model = _load(FAIL_SAMPLE)
    # Raise threshold so even the previously compliant 1100 mm door fails.
    model["meta"]["rule_config"]["exit_clear_width_mm_min"] = 1200
    result = run_checks(model)
    r1 = [f for f in result.findings if f.rule_id == "R1_EXIT_CLEAR_WIDTH"]
    assert {f.element_id: f.severity for f in r1} == {
        "D-STAIR-A": "fail",
        "D-STAIR-B": "fail",
    }


def test_r2_overlap_is_computed_not_tagged():
    model = _load(FAIL_SAMPLE)
    result = run_checks(model)
    stroller = next(f for f in result.findings if f.element_id == "F-STROLLER-01")
    assert stroller.severity == "fail"
    assert stroller.measured["overlap_m2"] > 0


def test_deterministic_explanation_lists_actions():
    model = _load(FAIL_SAMPLE)
    result = run_checks(model).to_dict()
    explanation = explain_findings(result, model=model)
    assert explanation["mode"] == "deterministic_agent"
    assert len(explanation["recommended_actions"]) == 3
    assert explanation["prompt_files"]["system"].endswith("compliance_agent_system.md")


def test_llm_prompt_templates_load_and_substitute():
    model = _load(FAIL_SAMPLE)
    result = run_checks(model).to_dict()
    rendered = _render_user_prompt(model, result)
    assert "{{MODEL_JSON}}" not in rendered
    assert "{{CHECK_RESULT_JSON}}" not in rendered
    assert "D-STAIR-B" in rendered
    assert "R1_EXIT_CLEAR_WIDTH" in rendered


def test_ifc_adapter_reads_door_widths():
    doors = extract_doors_from_ifc(IFC_SAMPLE)
    by_id = {d["id"]: d["clear_width_mm"] for d in doors}
    assert by_id["D-STAIR-A"] == 1100
    assert by_id["D-STAIR-B"] == 700


def test_ifc_adapter_merge_preserves_zones():
    base = _load(FAIL_SAMPLE)
    before_zones = copy.deepcopy(base["egress_zones"])
    merged = merge_ifc_doors_into_model(base, IFC_SAMPLE)
    assert merged["egress_zones"] == before_zones
    assert merged["meta"]["ifc_adapter"]["doors_imported"] == 2
    widths = {d["id"]: d["clear_width_mm"] for d in merged["doors"]}
    assert widths["D-STAIR-B"] == 700
