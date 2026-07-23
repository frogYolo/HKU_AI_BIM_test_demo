# How the building model is built

## Three layers (do not confuse them)

```
scripts/generate_sample_hk_tower_floor.py
        │
        ├── data/sample_hk_tower_floor.json      ← rules read THIS (doors, zones, furniture AABBs)
        ├── data/sample_hk_tower_floor.gltf      ← web / Blender look at THIS (visual only)
        └── data/sample_hk_tower_floor.ifc         ← optional BIM export (door widths)
```

**Pass/fail comes only from JSON + `checker/rules.py`.**  
The glTF is for communication; it does not decide compliance.  
`checker/ifc_adapter.py` can merge `IfcDoor.OverallWidth` into the JSON `doors[]` schema (stub, no ifcopenshell).

## JSON structure (what you edit for tests)

| Key | Meaning |
|-----|---------|
| `doors[]` | Fire stair doors — `clear_width_mm`, `is_exit` |
| `egress_zones[]` | Stair landing keep-clear rectangles (`aabb`) |
| `furniture[]` | Strollers, cartons — each has `aabb` for R2 clash |

## Rule code

`checker/rules.py`:
- **R1** `_check_exit_door_width()` — reads `doors[].clear_width_mm`
- **R2** `_check_egress_clashes()` — compares `furniture[].aabb` vs `egress_zones[].aabb`

## Sample JSON files

| File | Purpose |
|------|---------|
| `sample_hk_tower_floor.json` | Main demo — **3 fails** |
| `sample_hk_tower_floor_compliant.json` | Upload / comparison — **all pass** |

Regenerate both:

```bash
python scripts/generate_sample_hk_tower_floor.py
```

Verify:

```bash
python -m checker.cli data/sample_hk_tower_floor.json
python -m checker.cli data/sample_hk_tower_floor_compliant.json
python -m pytest -q
```

## Building typology

The sample is a **typical high-rise residential corridor slice** (21–25/F context, active 23/F), not a reconstruction of any specific project.

## Fix "Sample missing" error in browser

From the repository root:

```bash
python scripts/generate_sample_hk_tower_floor.py
python -m uvicorn app:app --reload --port 8000
```

Hard refresh the page (Ctrl+F5).
