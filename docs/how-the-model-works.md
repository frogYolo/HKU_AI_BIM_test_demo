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

## Test JSON files (how many?)

You only need **two**:

| File | Purpose |
|------|---------|
| `sample_hk_tower_floor.json` | Main demo — **3 fails** |
| `sample_hk_tower_floor_compliant.json` | Upload test — **all pass** |

Regenerate both:

```bash
python scripts/generate_sample_hk_tower_floor.py
```

Verify:

```bash
python -m checker.cli data/sample_hk_tower_floor.json
python -m checker.cli data/sample_hk_tower_floor_compliant.json
```

No need for many JSON files — one fail case + one pass case is enough for the video.

## Not 唐楼 — why?

We switched per your **宏福苑 / 高层应急** narrative:

- **唐楼** = low-rise mixed-use (shop + residential, ~6–10 storeys)
- **Current model** = **typical high-rise residential corridor slice** (21–25/F context, active 23/F)

This matches high-rise fire egress debate, not tong lau streetscape.

If you want **唐楼** instead, that is a different geometry (street frontage, rear stair, shop front) — say so and we can switch.

## Fix "Sample missing" error in browser

Your screenshot shows the **old server** still looking for `sample_classroom.py`. Restart:

```bash
cd d:\Cursor\hku-ai-bim-compliance-check
python scripts/generate_sample_hk_tower_floor.py
python -m uvicorn app:app --reload --port 8000
```

Hard refresh the page (Ctrl+F5).
