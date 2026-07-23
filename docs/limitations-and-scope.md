# Limitations & scope

This is a scoped egress micro-prototype, not a production BIM check platform.

## What we claim

| Claim | Evidence |
|-------|----------|
| Two deterministic egress rules | `checker/rules.py` |
| Plan geometry for R2 | AABB overlap area (m²), not a pre-baked "blocked" flag |
| Configurable threshold | `meta.rule_config.exit_clear_width_mm_min` in JSON |
| Clear width semantics | Field `clear_width_mm` documented; not confused with gross opening |
| Human–AI loop | Rules = truth; `explain.py` + `prompts/` = narration |
| IFC awareness | Minimal `sample_hk_tower_floor.ifc` + `checker/ifc_adapter.py` (OverallWidth→JSON); JSON remains check source |

## Scope notes

### Synthetic data

Expected for a micro-prototype. The repo ships a **stub** `checker/ifc_adapter.py` (STEP parse of `IfcDoor.OverallWidth`) that fills the same JSON schema. A fuller path would use ifcopenshell plus project property-set mapping. This is **not** production-ready on messy Revit/IFC exports.

### Geometry depth

R2 is **not** a boolean tag on the zone. It computes **2D AABB intersection** between `furniture[].aabb` and `egress_zones[].aabb` and reports overlap m². That is a simplified geometric check — not full 3D solid clash.

### Thresholds

900 mm is a **demo default**, not a claim about full fire-code compliance. Threshold lives in `meta.rule_config` and can be set per project (e.g. 1200 mm for primary exits).

### Clear vs gross width

JSON uses explicit `clear_width_mm`. Production IFC import would need property mapping (see `rule_config.width_semantics_note`). This demo shows the **check logic** once semantics are resolved.

### Spatial context

The viewer shows a typical floor corridor slice inside a multi-storey shell (21–25/F). Checking is floor-local by design.

### AI role

Rules engine is in Python; thresholds are in JSON. AI (`prompts/` + optional LLM mode) explains findings — it does **not** invent or override pass/fail.

## Summary

Configurable deterministic rules on explicit semantics, plan geometry for landing clash, and an explanation layer — with a documented IFC door-width import stub, not a claim of full code compliance.
