# HK High-Rise Corridor — Fire Egress Compliance Demo

HKU AI+BIM technical assessment prototype: **synthetic typical residential floor corridor** with two fire-egress checks.

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
```

Blender: import `data/sample_hk_tower_floor.gltf`

## Explanation modes

Deterministic rules in `checker/rules.py` are always the source of truth for pass/fail.
`checker/explain.py` supports two explanation modes:

- `deterministic` (default): template-style deterministic narration
- `llm`: LLM-generated narrative/actions based on deterministic findings

Configure with environment variables:

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
scripts/generate_sample_hk_tower_floor.py
data/sample_hk_tower_floor.*
web/                          Three.js viewer
prompts/
```
