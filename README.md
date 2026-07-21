# HK High-Rise Corridor — Fire Egress Compliance Demo

HKU AI+BIM technical assessment prototype: **synthetic typical residential floor corridor** with two fire-egress checks.

> Motivated by renewed Hong Kong debate on high-rise emergency design — **not** an incident reconstruction.

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

## Narrative for video (30 s)

1. HK towers rely on **corridors + fire stairs** for evacuation  
2. Design defects (narrow doors) and **daily occupation** (strollers, cartons) both matter in emergencies  
3. This tool runs **two deterministic checks** on synthetic data; AI explains fixes  

See [`docs/design-notes.md`](docs/design-notes.md) for scope and ethical framing.

## Layout

```
checker/rules.py              ← R1 + R2 (source of truth)
scripts/generate_sample_hk_tower_floor.py
data/sample_hk_tower_floor.*
web/                          Three.js viewer
prompts/
```
