# HK High-Rise Corridor — Fire Egress Compliance Demo

Synthetic typical Hong Kong residential floor corridor with two fire-egress checks.

**Check source of truth = JSON + `checker/rules.py`.**  
glTF is visualisation only. IFC is a minimal door sample; `checker/ifc_adapter.py` merges `IfcDoor.OverallWidth` into the same JSON schema (stub — not full ifcopenshell).

## Rules

| ID | Rule | Demo failure |
|----|------|--------------|
| **R1** | Fire stair door clear width ≥ **900 mm** | **D-STAIR-B** = 700 mm |
| **R2** | No obstruction in stair landing clear zone | **F-STROLLER-01** + **F-CARTON-01** vs **EZ-STAIR-B** |

## Quick start

```bash
python -m pip install -r requirements.txt
python scripts/generate_sample_hk_tower_floor.py
python -m uvicorn app:app --reload --port 8000
```

Open http://127.0.0.1:8000

```bash
python -m checker.cli data/sample_hk_tower_floor.json
python -m pytest -q
```

Blender: import `data/sample_hk_tower_floor.gltf`

## Data layers

| File | Role |
|------|------|
| `data/sample_hk_tower_floor.json` | **Rules engine input** (doors, egress zones, furniture AABBs) |
| `data/sample_hk_tower_floor.gltf` | Web / Blender look only |
| `data/sample_hk_tower_floor.ifc` | Minimal IFC doors; adapter merges widths → JSON |

```bash
# Merge IFC door widths into the JSON schema, then check
python -c "import json; from pathlib import Path; from checker.ifc_adapter import merge_ifc_doors_into_model; from checker.rules import run_checks; m=json.loads(Path('data/sample_hk_tower_floor.json').read_text(encoding='utf-8')); m=merge_ifc_doors_into_model(m,'data/sample_hk_tower_floor.ifc'); print(run_checks(m).summary)"
```

## Explanation modes

Deterministic rules in `checker/rules.py` are always the source of truth for pass/fail.  
`checker/explain.py` loads **`prompts/compliance_agent_system.md`** and **`prompts/compliance_agent_user.md`** when `EXPLAIN_MODE=llm`.

- `deterministic` (default): template-style deterministic narration
- `llm`: LLM narration/actions from those prompt files + deterministic findings

```bash
# default mode (stable/offline)
EXPLAIN_MODE=deterministic

# optional LLM mode
EXPLAIN_MODE=llm
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

If LLM mode fails (missing key/package/API error), the app automatically falls back to deterministic explanation.

## Sample data

- `data/sample_hk_tower_floor.json`: mixed result sample (**3 fail, 2 pass**)
- `data/sample_hk_tower_floor_compliant.json`: compliant sample (**0 fail**)

## Layout

```
checker/rules.py              ← R1 + R2 (source of truth)
checker/explain.py            ← loads prompts/ in LLM mode
checker/ifc_adapter.py        ← IFC OverallWidth → JSON doors stub
prompts/                      ← system + user prompt files
tests/test_rules.py
scripts/generate_sample_hk_tower_floor.py
data/sample_hk_tower_floor.*
web/                          Three.js viewer
docs/
```

## Docs

- `docs/design-notes.md` — why these two rules
- `docs/how-the-model-works.md` — JSON / glTF / IFC roles
- `docs/limitations-and-scope.md` — scope and limitations
