"""
Synthetic HK high-rise residential typical floor corridor.

Motivation: preventive checks for recurring emergency-path issues discussed
after recent Hong Kong tower fire safety debates — NOT a recreation of any
specific incident or real floor plan.

Outputs: data/sample_hk_tower_floor.{json,gltf,bin,ifc}
"""

from __future__ import annotations

import copy
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CORRIDOR_L = 22.0
CORRIDOR_W = 2.6
WALL_H = 2.85
WALL_T = 0.15
DOOR_H = 2.1
LINTEL = WALL_H - DOOR_H

# Palette — HK public / private residential corridor feel
M_TILE_A = [0.82, 0.80, 0.76, 1.0]
M_TILE_B = [0.76, 0.74, 0.70, 1.0]
M_WALL = [0.90, 0.89, 0.87, 1.0]
M_WALL_LOWER = [0.78, 0.82, 0.84, 1.0]
M_FRAME = [0.55, 0.38, 0.22, 1.0]  # flat door wood tone
M_FIRE_FRAME = [0.32, 0.34, 0.36, 1.0]
M_FLAT_DOOR = [0.62, 0.42, 0.28, 1.0]
M_LIFT = [0.72, 0.74, 0.76, 1.0]
M_LIFT_FRAME = [0.45, 0.47, 0.50, 1.0]
M_SIGN_OK = [0.12, 0.62, 0.32, 1.0]
M_SIGN_FAIL = [0.82, 0.14, 0.10, 1.0]
M_HOSE = [0.88, 0.22, 0.18, 1.0]
M_STROLLER = [0.35, 0.38, 0.42, 1.0]
M_CARTON = [0.72, 0.58, 0.38, 1.0]
M_ZONE_OK = [0.18, 0.62, 0.38, 0.30]
M_ZONE_FAIL = [0.92, 0.16, 0.10, 0.38]
M_CEIL = [0.94, 0.94, 0.93, 1.0]
M_LIGHT = [0.98, 0.98, 0.95, 1.0]
M_DOOR_OK = [0.16, 0.50, 0.34, 1.0]
M_DOOR_FAIL = [0.78, 0.20, 0.16, 1.0]
M_TOWER = [0.82, 0.80, 0.78, 1.0]
M_TOWER_GHOST = [0.78, 0.76, 0.74, 0.45]
M_WINDOW = [0.62, 0.78, 0.92, 0.55]
M_FLOOR_LABEL = [0.15, 0.18, 0.22, 1.0]

ACTIVE_STOREY = 23
FLOOR_BANDS = (21, 22, 23, 24, 25)
UNIT_DEPTH = 3.0
CORE_DEPTH = 2.8
BUILDING_WEST = -UNIT_DEPTH
BUILDING_EAST = CORRIDOR_W + CORE_DEPTH
FACADE_X = BUILDING_EAST - WALL_T / 2
BAND_H = WALL_H + 0.12  # show tower height context


def box(name, cx, cy, cz, sx, sy, sz, rgba):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    corners = [
        [cx - hx, cy - hy, cz - hz],
        [cx + hx, cy - hy, cz - hz],
        [cx + hx, cy + hy, cz - hz],
        [cx - hx, cy + hy, cz - hz],
        [cx - hx, cy - hy, cz + hz],
        [cx + hx, cy - hy, cz + hz],
        [cx + hx, cy + hy, cz + hz],
        [cx - hx, cy + hy, cz + hz],
    ]
    indices = [
        0, 1, 2, 0, 2, 3,
        4, 6, 5, 4, 7, 6,
        0, 4, 5, 0, 5, 1,
        1, 5, 6, 1, 6, 2,
        2, 6, 7, 2, 7, 3,
        3, 7, 4, 3, 4, 0,
    ]
    return {"name": name, "corners": corners, "indices": indices, "rgba": rgba}


def aabb(cx, cz, sx, sz):
    return {"min": [cx - sx / 2, cz - sz / 2], "max": [cx + sx / 2, cz + sz / 2]}


def wall_opening_z(meshes, name, x, z0, z1, oz, ow, rgba=M_WALL):
    half = ow / 2
    a, b = oz - half, oz + half
    if a - z0 > 0.05:
        meshes.append(box(f"{name}-A", x, WALL_H / 2, (z0 + a) / 2, WALL_T, WALL_H, a - z0, rgba))
    if z1 - b > 0.05:
        meshes.append(box(f"{name}-B", x, WALL_H / 2, (b + z1) / 2, WALL_T, WALL_H, z1 - b, rgba))
    meshes.append(box(f"{name}-lintel", x, DOOR_H + LINTEL / 2, oz, WALL_T, LINTEL, ow, rgba))


def add_fire_door(meshes, door_id, x, z, width_m, axis, rgba, fail=False):
    ft = 0.08
    th = 0.06
    if axis == "z":
        meshes.append(box(f"{door_id}-frame-L", x, DOOR_H / 2, z - width_m / 2, 0.16, DOOR_H, ft, M_FIRE_FRAME))
        meshes.append(box(f"{door_id}-frame-R", x, DOOR_H / 2, z + width_m / 2, 0.16, DOOR_H, ft, M_FIRE_FRAME))
        meshes.append(box(f"{door_id}-frame-T", x, DOOR_H, z, 0.16, ft, width_m + 0.06, M_FIRE_FRAME))
        meshes.append(box(door_id, x, DOOR_H / 2, z, th, DOOR_H - 0.08, width_m - 0.08, rgba))
        sign = M_SIGN_FAIL if fail else M_SIGN_OK
        meshes.append(box(f"{door_id}-sign", x - 0.20, DOOR_H + 0.22, z, 0.45, 0.14, 0.22, sign))
    else:
        meshes.append(box(f"{door_id}-frame-L", x - width_m / 2, DOOR_H / 2, z, ft, DOOR_H, 0.16, M_FIRE_FRAME))
        meshes.append(box(f"{door_id}-frame-R", x + width_m / 2, DOOR_H / 2, z, ft, DOOR_H, 0.16, M_FIRE_FRAME))
        meshes.append(box(f"{door_id}-frame-T", x, DOOR_H, z, width_m + 0.06, ft, 0.16, M_FIRE_FRAME))
        meshes.append(box(door_id, x, DOOR_H / 2, z, width_m - 0.08, DOOR_H - 0.08, th, rgba))
        sign = M_SIGN_FAIL if fail else M_SIGN_OK
        meshes.append(box(f"{door_id}-sign", x, DOOR_H + 0.22, z + 0.18, 0.22, 0.14, 0.45, sign))


def add_flat_door(meshes, flat_id, x, z):
    meshes.append(box(f"{flat_id}-door", x + 0.06, DOOR_H / 2, z, 0.10, DOOR_H - 0.05, 0.85, M_FLAT_DOOR))
    meshes.append(box(f"{flat_id}-frame", x + 0.02, DOOR_H / 2, z, 0.04, DOOR_H, 0.92, M_FRAME))
    meshes.append(box(f"{flat_id}-num", x + 0.12, 1.45, z, 0.02, 0.12, 0.18, M_FIRE_FRAME))


def add_lift_bank(meshes, cx, cz):
    for i, off in enumerate((-1.1, 0.0, 1.1)):
        lid = f"Lift-{i+1}"
        meshes.append(box(lid, cx, 1.35, cz + off, 0.12, 2.7, 1.05, M_LIFT))
        meshes.append(box(f"{lid}-frame", cx - 0.06, 1.35, cz + off, 0.06, 2.75, 1.12, M_LIFT_FRAME))
        meshes.append(box(f"{lid}-panel", cx + 0.08, 1.05, cz + off, 0.03, 0.45, 0.35, M_LIGHT))


def add_stroller(meshes, fid, x, z):
    meshes.append(box(fid, x, 0.55, z, 0.55, 1.1, 0.85, M_STROLLER))
    meshes.append(box(f"{fid}-hood", x + 0.15, 0.95, z - 0.25, 0.35, 0.35, 0.35, M_STROLLER))
    meshes.append(box(f"{fid}-wheel-L", x - 0.18, 0.12, z + 0.25, 0.12, 0.24, 0.12, M_FIRE_FRAME))
    meshes.append(box(f"{fid}-wheel-R", x + 0.18, 0.12, z + 0.25, 0.12, 0.24, 0.12, M_FIRE_FRAME))


def add_cartons(meshes, fid, x, z):
    meshes.append(box(f"{fid}-1", x - 0.2, 0.35, z, 0.45, 0.7, 0.45, M_CARTON))
    meshes.append(box(f"{fid}-2", x + 0.25, 0.25, z + 0.1, 0.35, 0.5, 0.35, M_CARTON))


def add_facade_window(meshes, name, x_face, y_base, z, active=True):
    """Window flush with east facade plane."""
    ww, wh = 1.25, 1.15
    cy = y_base + 1.35
    # recess into wall
    meshes.append(box(f"{name}-frame", x_face - 0.04, cy, z, 0.10, wh + 0.12, ww + 0.12, M_FRAME))
    meshes.append(box(f"{name}-glass", x_face - 0.07, cy, z, 0.04, wh, ww, M_WINDOW if active else [0.55, 0.68, 0.82, 0.35]))


def add_tower_stack(meshes):
    """Unified multi-storey shell — windows and slabs share one building envelope."""
    cx = (BUILDING_WEST + BUILDING_EAST) / 2
    bx = BUILDING_EAST - BUILDING_WEST

    for floor in FLOOR_BANDS:
        dy = (floor - ACTIVE_STOREY) * BAND_H
        is_active = floor == ACTIVE_STOREY

        # Floor slab (one continuous deck per level)
        meshes.append(
            box(
                f"Slab-{floor}F",
                cx,
                dy - 0.02,
                CORRIDOR_L / 2,
                bx,
                0.12,
                CORRIDOR_L + 0.35,
                M_TOWER if is_active else M_TOWER_GHOST,
            )
        )

        # Perimeter shell (4 walls) — ghost floors are solid blocks; active floor gets interior cutaway later
        wall_rgba = M_TOWER if is_active else M_TOWER_GHOST
        # East facade
        meshes.append(
            box(f"Shell-East-{floor}F", FACADE_X, dy + WALL_H / 2, CORRIDOR_L / 2, WALL_T, WALL_H, CORRIDOR_L + 0.2, wall_rgba)
        )
        # West facade (unit side)
        meshes.append(
            box(
                f"Shell-West-{floor}F",
                BUILDING_WEST + WALL_T / 2,
                dy + WALL_H / 2,
                CORRIDOR_L / 2,
                WALL_T,
                WALL_H,
                CORRIDOR_L + 0.2,
                wall_rgba,
            )
        )
        # North / south end caps
        meshes.append(box(f"Shell-North-{floor}F", cx, dy + WALL_H / 2, CORRIDOR_L, bx, WALL_H, WALL_T, wall_rgba))
        meshes.append(box(f"Shell-South-{floor}F", cx, dy + WALL_H / 2, 0.0, bx, WALL_H, WALL_T, wall_rgba))

        # Windows flush on east facade
        for zi in (3.5, 8.0, 12.5, 17.0, 21.0):
            add_facade_window(meshes, f"Win-{floor}F-{int(zi)}", FACADE_X, dy, zi, active=is_active)

        # Floor label on west facade
        meshes.append(
            box(
                f"Label-{floor}F",
                BUILDING_WEST + 0.12,
                dy + 2.2,
                1.0,
                0.03,
                0.28,
                0.55,
                M_FLOOR_LABEL if is_active else [0.35, 0.35, 0.38, 0.55],
            )
        )


def add_flat_units(meshes):
    for i, z in enumerate((2.5, 5.5, 8.5, 14.0, 17.0, 19.5)):
        uid = f"Unit-{i+1:02d}"
        cx = BUILDING_WEST + UNIT_DEPTH / 2
        meshes.append(box(uid, cx, 1.35, z, UNIT_DEPTH - 0.25, WALL_H - 0.25, 2.0, [0.86, 0.84, 0.82, 1.0]))
        meshes.append(box(f"{uid}-floor", cx, 0.04, z, UNIT_DEPTH - 0.35, 0.06, 1.85, M_TILE_B))


def build_compliant_model() -> dict:
    """All issues fixed — use for pass-case demo / upload test."""
    model = copy.deepcopy(build_semantic_model())
    for door in model["doors"]:
        if door["id"] == "D-STAIR-B":
            door["clear_width_mm"] = 1100
            door["notes"] = "Upgraded to compliant width"
    model["furniture"] = [
        f
        for f in model["furniture"]
        if f["id"] not in ("F-STROLLER-01", "F-CARTON-01")
    ]
    model["meta"]["name"] = "Synthetic HK Tower Floor — Compliant variant"
    return model


def build_semantic_model() -> dict:
    doors = [
        {
            "id": "D-STAIR-A",
            "name": "Fire Stair A (near lift lobby)",
            "is_exit": True,
            "clear_width_mm": 1100,
            "height_mm": 2100,
            "axis": "z",
            "location": {"x": CORRIDOR_W, "y": 3.5},
            "notes": "Compliant fire-rated stair door",
        },
        {
            "id": "D-STAIR-B",
            "name": "Fire Stair B (remote end)",
            "is_exit": True,
            "clear_width_mm": 700,
            "height_mm": 2100,
            "axis": "z",
            "location": {"x": CORRIDOR_W, "y": 20.5},
            "notes": "Design defect demo: door below 900 mm clear width",
        },
    ]

    egress_zones = [
        {
            "id": "EZ-STAIR-A",
            "door_id": "D-STAIR-A",
            "name": "Stair A landing clear zone",
            "aabb": aabb(CORRIDOR_W - 0.85, 3.5, 1.35, 1.5),
        },
        {
            "id": "EZ-STAIR-B",
            "door_id": "D-STAIR-B",
            "name": "Stair B landing clear zone",
            "aabb": aabb(CORRIDOR_W - 0.85, 20.2, 1.5, 1.45),
        },
    ]

    furniture = [
        {
            "id": "F-STROLLER-01",
            "name": "Stroller parked at stair landing",
            "kind": "obstruction",
            "aabb": aabb(CORRIDOR_W - 0.75, 20.15, 0.65, 0.95),
            "center": [CORRIDOR_W - 0.75, 20.15],
            "size": [0.65, 0.95],
            "intentional_issue": "Blocks EZ-STAIR-B — common corridor occupation issue",
        },
        {
            "id": "F-CARTON-01",
            "name": "Renovation cartons at stair landing",
            "kind": "obstruction",
            "aabb": aabb(1.35, 20.35, 0.55, 0.55),
            "center": [1.35, 20.35],
            "size": [0.55, 0.55],
            "intentional_issue": "Partial overlap with EZ-STAIR-B",
        },
    ]

    return {
        "meta": {
            "name": "Synthetic HK Tower Residential Floor — Corridor Segment",
            "space_type": "hk_residential_corridor",
            "source": "scripts/generate_sample_hk_tower_floor.py",
            "units": {"length": "meter", "door_width": "millimeter"},
            "formats": ["json", "gltf", "ifc"],
            "rules_targeted": [
                "R1 fire stair door clear_width_mm >= 900",
                "R2 obstructions must not intersect stair landing clear zones",
            ],
            "motivation": (
                "Preventive micro-prototype inspired by renewed Hong Kong debate on "
                "high-rise residential emergency design and corridor occupation — "
                "synthetic geometry only, not any real building or incident reconstruction."
            ),
            "disclaimer": "Academic demo. Not based on proprietary or incident-specific data.",
            "rule_config": {
                "exit_clear_width_mm_min": 900,
                "width_semantics": "clear_width_mm",
                "width_semantics_note": (
                    "Explicit net clear width in JSON — not IfcDoor.OverallWidth without review. "
                    "Production path: map Pset_DoorCommon / local parameter with gross-to-clear deduction."
                ),
                "jurisdiction_note": (
                    "900 mm is the default demo threshold. Primary tower exits may require 1100–1200 mm "
                    "under project-specific fire engineering — change exit_clear_width_mm_min in JSON."
                ),
            },
        },
        "building": {
            "id": "B-HK-T01",
            "name": "Typical Tower — 23/F Corridor",
            "storey": "23/F",
            "footprint_m": {"width": CORRIDOR_W, "depth": CORRIDOR_L, "height": WALL_H},
        },
        "doors": doors,
        "egress_zones": egress_zones,
        "furniture": furniture,
    }


def build_meshes(model: dict) -> list[dict]:
    meshes: list[dict] = []
    doors = {d["id"]: d for d in model["doors"]}
    furn_ids = {f["id"] for f in model.get("furniture", [])}

    # Single-floor cutaway (3D is context only; plan view is primary)
    tile = 1.1
    for iz in range(int(CORRIDOR_L / tile) + 2):
        for ix in range(int(CORRIDOR_W / tile) + 2):
            x0 = ix * tile
            z0 = iz * tile
            if x0 >= CORRIDOR_W or z0 >= CORRIDOR_L:
                continue
            sx = min(tile, CORRIDOR_W - x0)
            sz = min(tile, CORRIDOR_L - z0)
            cx, cz = x0 + sx / 2, z0 + sz / 2
            rgba = M_TILE_A if (ix + iz) % 2 == 0 else M_TILE_B
            meshes.append(box(f"Tile-{ix}-{iz}", cx, -0.03, cz, sx, 0.06, sz, rgba))

    meshes.append(box("Ceiling", CORRIDOR_W / 2, WALL_H + 0.03, CORRIDOR_L / 2, CORRIDOR_W - 0.05, 0.04, CORRIDOR_L - 0.1, M_CEIL))

    # Fluorescent strip lights along corridor
    for z in (4, 8, 12, 16, 20):
        meshes.append(box(f"Light-{z}", CORRIDOR_W / 2, WALL_H - 0.06, z, 0.35, 0.05, 1.8, M_LIGHT))

    # Interior partition: corridor west (flat doors) — sits inside shell
    meshes.append(box("Wall-West", WALL_T / 2, WALL_H / 2, CORRIDOR_L / 2, WALL_T, WALL_H, CORRIDOR_L, M_WALL))
    meshes.append(box("Wall-West-Lower", 0.10, 0.55, CORRIDOR_L / 2, 0.06, 1.1, CORRIDOR_L, M_WALL_LOWER))

    # Interior partition: corridor east (lift / stair side)
    d_a = doors["D-STAIR-A"]
    d_b = doors["D-STAIR-B"]
    w_a = d_a["clear_width_mm"] / 1000
    w_b = d_b["clear_width_mm"] / 1000
    x_e = CORRIDOR_W - WALL_T / 2
    wall_opening_z(meshes, "Wall-East-A", x_e, 0.0, 8.0, d_a["location"]["y"], w_a + 0.14)
    wall_opening_z(meshes, "Wall-East-B", x_e, 16.0, CORRIDOR_L, d_b["location"]["y"], w_b + 0.14)
    meshes.append(box("Wall-East-Mid", x_e, WALL_H / 2, 12.0, WALL_T, WALL_H, 8.0, M_WALL))

    # Core wall between corridor and external shell (lift/stair zone)
    meshes.append(box("Wall-Core", CORRIDOR_W + 0.55, WALL_H / 2, CORRIDOR_L / 2, 0.12, WALL_H, CORRIDOR_L, [0.84, 0.85, 0.87, 1.0]))

    # Flat doors + unit volumes behind them
    for i, z in enumerate((2.5, 5.5, 8.5, 14.0, 17.0, 19.5)):
        add_flat_door(meshes, f"Flat-{i+1:02d}", WALL_T, z)
    add_flat_units(meshes)

    meshes.append(box("Lift-Lobby", CORRIDOR_W + 0.95, WALL_H / 2, 11.0, 1.2, WALL_H - 0.1, 3.6, [0.80, 0.82, 0.84, 1.0]))
    add_lift_bank(meshes, CORRIDOR_W + 0.75, 11.0)

    # Fire hose cabinet
    meshes.append(box("Hose-Reel", 0.10, 1.25, 10.8, 0.12, 0.9, 0.45, M_HOSE))
    meshes.append(box("Hose-Glass", 0.14, 1.25, 10.8, 0.03, 0.75, 0.35, M_LIGHT))

    # Fire stair doors
    for d in model["doors"]:
        fail = d["clear_width_mm"] < 900
        rgba = M_DOOR_FAIL if fail else M_DOOR_OK
        add_fire_door(
            meshes,
            d["id"],
            CORRIDOR_W - WALL_T / 2,
            d["location"]["y"],
            d["clear_width_mm"] / 1000,
            d["axis"],
            rgba,
            fail=fail,
        )

    # Obstructions — only if present in JSON (compliant variant omits them)
    if "F-STROLLER-01" in furn_ids:
        f = next(x for x in model["furniture"] if x["id"] == "F-STROLLER-01")
        add_stroller(meshes, "F-STROLLER-01", f["center"][0], f["center"][1])
    if "F-CARTON-01" in furn_ids:
        f = next(x for x in model["furniture"] if x["id"] == "F-CARTON-01")
        add_cartons(meshes, "F-CARTON-01", f["center"][0], f["center"][1])

    # Egress zones — highlight any with clashes
    clash_zones: set[str] = set()

    def overlap_area(a, b):
        if a["max"][0] < b["min"][0] or b["max"][0] < a["min"][0]:
            return 0
        if a["max"][1] < b["min"][1] or b["max"][1] < a["min"][1]:
            return 0
        x0 = max(a["min"][0], b["min"][0])
        x1 = min(a["max"][0], b["max"][0])
        z0 = max(a["min"][1], b["min"][1])
        z1 = min(a["max"][1], b["max"][1])
        return max(0, x1 - x0) * max(0, z1 - z0)

    for z in model.get("egress_zones", []):
        za = z["aabb"]
        for f in model.get("furniture", []):
            if overlap_area(za, f["aabb"]) > 1e-6:
                clash_zones.add(z["id"])

    for z in model["egress_zones"]:
        mn, mx = z["aabb"]["min"], z["aabb"]["max"]
        cx, cz = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
        sx, sz = mx[0] - mn[0], mx[1] - mn[1]
        fail_zone = z["id"] in clash_zones
        rgba = M_ZONE_FAIL if fail_zone else M_ZONE_OK
        meshes.append(box(z["id"], cx, 0.07, cz, sx, 0.14, sz, rgba))
        bd = 0.035
        for bx, bz, bsx, bsz in (
            (cx, cz - sz / 2 + bd / 2, sx, bd),
            (cx, cz + sz / 2 - bd / 2, sx, bd),
            (cx - sx / 2 + bd / 2, cz, bd, sz),
            (cx + sx / 2 - bd / 2, cz, bd, sz),
        ):
            meshes.append(box(f"{z['id']}-edge", bx, 0.12, bz, bsx, 0.05, bsz, rgba[:3] + [0.75]))

    return meshes


def write_gltf(meshes: list[dict], path: Path) -> None:
    accessors, buffer_views, gltf_meshes, nodes, materials = [], [], [], [], []
    bin_parts: list[bytes] = []
    bin_offset = 0

    def align4(n: int) -> int:
        return (n + 3) & ~3

    for i, m in enumerate(meshes):
        pos = [v for c in m["corners"] for v in (float(c[0]), float(c[1]), float(c[2]))]
        idx = m["indices"]
        pos_bytes = struct.pack("<" + "f" * len(pos), *pos)
        idx_bytes = struct.pack("<" + "H" * len(idx), *idx)
        pos_padded = pos_bytes + b"\x00" * (align4(len(pos_bytes)) - len(pos_bytes))
        idx_padded = idx_bytes + b"\x00" * (align4(len(idx_bytes)) - len(idx_bytes))

        bv_pos = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": bin_offset, "byteLength": len(pos_bytes), "target": 34962})
        bin_offset += len(pos_padded)
        bin_parts.append(pos_padded)
        bv_idx = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": bin_offset, "byteLength": len(idx_bytes), "target": 34963})
        bin_offset += len(idx_padded)
        bin_parts.append(idx_padded)

        xs, ys, zs = zip(*m["corners"])
        acc_pos = len(accessors)
        accessors.append(
            {
                "bufferView": bv_pos,
                "componentType": 5126,
                "count": 8,
                "type": "VEC3",
                "max": [max(xs), max(ys), max(zs)],
                "min": [min(xs), min(ys), min(zs)],
            }
        )
        acc_idx = len(accessors)
        accessors.append({"bufferView": bv_idx, "componentType": 5123, "count": len(idx), "type": "SCALAR"})

        rgba = m["rgba"]
        mat = {
            "name": f"mat_{m['name']}",
            "pbrMetallicRoughness": {
                "baseColorFactor": rgba,
                "metallicFactor": 0.05,
                "roughnessFactor": 0.82,
            },
        }
        if rgba[3] < 0.99:
            mat["alphaMode"] = "BLEND"
            mat["doubleSided"] = True
        materials.append(mat)
        gltf_meshes.append(
            {
                "name": m["name"],
                "primitives": [
                    {"attributes": {"POSITION": acc_pos}, "indices": acc_idx, "material": len(materials) - 1}
                ],
            }
        )
        nodes.append({"name": m["name"], "mesh": i})

    blob = b"".join(bin_parts)
    gltf = {
        "asset": {"version": "2.0", "generator": "generate_sample_hk_tower_floor.py"},
        "scene": 0,
        "scenes": [{"name": "HKTowerCorridor", "nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": gltf_meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(blob), "uri": "sample_hk_tower_floor.bin"}],
    }
    path.write_text(json.dumps(gltf, indent=2), encoding="utf-8")
    path.with_suffix(".bin").write_bytes(blob)


def write_minimal_ifc(model: dict, path: Path) -> None:
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');",
        "FILE_NAME('sample_hk_tower_floor.ifc','2026-07-21T00:00:00',('Lu Yu'),('HKU AI+BIM demo'),"
        "'generate_sample_hk_tower_floor.py','generate_sample_hk_tower_floor.py','');",
        "FILE_SCHEMA(('IFC4'));",
        "ENDSEC;",
        "DATA;",
        "#1=IFCPERSON($,$,'Demo',$,$,$,$,$);",
        "#2=IFCORGANIZATION($,'Synthetic HK Tower Demo',$,$,$);",
        "#3=IFCPERSONANDORGANIZATION(#1,#2,$);",
        "#4=IFCAPPLICATION(#2,'0.2','HK Tower Egress Demo','HKTower');",
        "#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,$,$,0);",
        "#6=IFCCARTESIANPOINT((0.,0.,0.));",
        "#7=IFCDIRECTION((0.,0.,1.));",
        "#8=IFCDIRECTION((1.,0.,0.));",
        "#9=IFCAXIS2PLACEMENT3D(#6,#7,#8);",
        "#10=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.0E-5,#9,$);",
        "#12=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);",
        "#13=IFCUNITASSIGNMENT((#12));",
        "#14=IFCPROJECT('2ProjectHKTower000001',#5,'HK Tower Egress Demo',$,$,$,$,(#10),#13);",
        "#20=IFCCARTESIANPOINT((0.,0.,0.));",
        "#21=IFCAXIS2PLACEMENT3D(#20,#7,#8);",
        "#22=IFCLOCALPLACEMENT($,#21);",
        "#23=IFCSITE('2SiteHKTower00000001',#5,'Site',$,$,#22,$,$,.ELEMENT.,$,$,0.,$,$);",
        "#24=IFCRELAGGREGATES('2RelAggProject0000001',#5,$,$,#14,(#23));",
        "#30=IFCCARTESIANPOINT((0.,0.,0.));",
        "#31=IFCAXIS2PLACEMENT3D(#30,#7,#8);",
        "#32=IFCLOCALPLACEMENT(#22,#31);",
        "#33=IFCBUILDING('2BuildingHKTower00001',#5,'Residential Tower',$,$,#32,$,$,.ELEMENT.,$,$,$);",
        "#34=IFCRELAGGREGATES('2RelAggSite000000001',#5,$,$,#23,(#33));",
        "#40=IFCCARTESIANPOINT((0.,0.,0.));",
        "#41=IFCAXIS2PLACEMENT3D(#40,#7,#8);",
        "#42=IFCLOCALPLACEMENT(#32,#41);",
        "#43=IFCBUILDINGSTOREY('2StoreyHKTower000001',#5,'23/F',$,$,#42,$,$,.ELEMENT.,0.);",
        "#44=IFCRELAGGREGATES('2RelAggBldg000000001',#5,$,$,#33,(#43));",
        "#50=IFCSPACE('2SpaceCorridor00000001',#5,'Corridor','Typical floor corridor',$,#42,$,'COR-23F',.ELEMENT.,.INTERNAL.,$);",
        "#51=IFCRELCONTAINEDINSPATIALSTRUCTURE('2RelSpace0000000001',#5,$,$,(#50),#43);",
    ]
    n = 100
    door_ids = []
    for door in model["doors"]:
        width_m = door["clear_width_mm"] / 1000.0
        height_m = door["height_mm"] / 1000.0
        x = float(door["location"]["x"])
        y = float(door["location"]["y"])
        pid = n
        lines.append(f"#{pid}=IFCCARTESIANPOINT(({x:.3f},{y:.3f},0.));")
        lines.append(f"#{pid+1}=IFCAXIS2PLACEMENT3D(#{pid},#7,#8);")
        lines.append(f"#{pid+2}=IFCLOCALPLACEMENT(#42,#{pid+1});")
        door_ent = pid + 3
        lines.append(
            f"#{door_ent}=IFCDOOR('2Door{door['id'].replace('-', '')}00001',#5,'{door['name']}',"
            f"'{door.get('notes','')}',$,#{pid+2},$,'{door['id']}',.DOOR.,"
            f"{height_m:.3f},{width_m:.3f},$,$);"
        )
        door_ids.append(door_ent)
        n = pid + 8
    door_list = ",".join(f"#{i}" for i in door_ids)
    lines.append(
        f"#{n}=IFCRELCONTAINEDINSPATIALSTRUCTURE('2RelDoors0000000001',#5,$,$,({door_list}),#43);"
    )
    lines += ["ENDSEC;", "END-ISO-10303-21;"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    # Default: issues present (fail demo)
    model_fail = build_semantic_model()
    (DATA / "sample_hk_tower_floor.json").write_text(
        json.dumps(model_fail, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    meshes = build_meshes(model_fail)
    write_gltf(meshes, DATA / "sample_hk_tower_floor.gltf")
    write_minimal_ifc(model_fail, DATA / "sample_hk_tower_floor.ifc")

    # Compliant variant for upload / pass-case test
    model_ok = build_compliant_model()
    (DATA / "sample_hk_tower_floor_compliant.json").write_text(
        json.dumps(model_ok, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"meshes (fail case glTF): {len(meshes)}")
    print("Wrote data/sample_hk_tower_floor.json       (3 fails — main demo)")
    print("Wrote data/sample_hk_tower_floor_compliant.json (all pass — upload test)")
    for d in model_fail["doors"]:
        flag = "FAIL" if d["clear_width_mm"] < 900 else "ok"
        print(f"  {d['id']}: {d['clear_width_mm']}mm [{flag}]")


if __name__ == "__main__":
    main()
