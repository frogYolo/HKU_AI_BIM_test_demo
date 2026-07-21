# Limitations & scope (honest defence for reviewers)

This is a **7-day HKU AI+BIM micro-prototype**, not a production BIM Check Platform.

## What we claim

| Claim | Evidence |
|-------|----------|
| Two deterministic egress rules | `checker/rules.py` |
| Plan geometry for R2 | AABB overlap area (m²), not a pre-baked "blocked" flag |
| Configurable threshold | `meta.rule_config.exit_clear_width_mm_min` in JSON |
| Clear width semantics | Field `clear_width_mm` documented; not confused with gross opening |
| Human–AI loop | Rules = truth; `explain.py` + `prompts/` = narration |
| IFC awareness | Minimal `sample_hk_tower_floor.ifc`; JSON is check source for demo |

## Red-team critique → response

### “Only sterile synthetic data”

**Fair for production. Expected for this test.**

Task brief allows JSON / generated samples. We document IFC mapping and state that **next step = ifcopenshell adapter** to populate the same JSON schema from real exports. We do **not** claim production readiness on messy Revit/IFC without an adapter layer.

### “Tagging not geometry”

**Partially unfair.**

R2 is **not** a boolean tag on the zone. It computes **2D AABB intersection** between `furniture[].aabb` and `egress_zones[].aabb` and reports overlap m². That is a simplified geometric check — not full 3D BREP clash. We say so explicitly.

Full IFC solid–solid clash is out of scope for 1–2 rules in 7 days.

### “900 mm is wrong for HK tower”

**Fair that real projects vary.**

900 mm is a **demo default**, not a claim about full HK fire code compliance. Threshold lives in `meta.rule_config` and can be set to 1200 mm for primary exits. Video/README should say: *human sets criteria per project*.

### “Clear vs gross width”

**Fair for IFC auto-import.**

JSON uses explicit `clear_width_mm`. Production would need property mapping rules (documented in `rule_config.width_semantics_note`). This demo shows the **check logic** once semantics are resolved — not the full IFC property resolver.

### “Contextless 3D island”

**Partially fair.**

We show a **typical floor corridor slice** inside a multi-storey shell (21–25/F). Checking is floor-local by design. Room linkage = flat doors `Flat-01…06` on west side; extend with `IfcSpace` relations in v2.

### “Report not actionable”

**Partially unfair.**

`explain.py` returns `recommended_actions` (widen door X, remove stroller Y from zone Z). UI lists them under **Suggested actions**. If fails show without actions, check API response / refresh cache.

### “Hardcoded rules / fake AI”

**Partially fair on UI copy.**

Rules engine is in Python, threshold in JSON. AI role = **research + explanation** (prompts in repo), not LLM-as-judge. Title “AI+BIM” matches task wording (“AI-native learning”, “prompts in GitHub”) — we do not claim GPT runs the compliance verdict.

## One sentence for the video

> “This is a scoped egress micro-prototype: configurable deterministic rules on explicit semantics, plan geometry for landing clash, and an AI layer for explanation — with a documented path to IFC import, not a claim of full code compliance.”
