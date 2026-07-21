"""
Generate a synthetic classroom for fire-egress compliance demos.

Outputs (under data/):
  sample_classroom.json / .gltf / .bin / .ifc
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

ROOM_W = 12.0
ROOM_D = 9.0
WALL_H = 3.2
WALL_T = 0.15
DOOR_H = 2.1
LINTEL = WALL_H - DOOR_H
BASE_H = 0.12

# Materials
M_FLOOR = [0.72, 0.68, 0.60, 1.0]
M_AISLE = [0.78, 0.74, 0.66, 1.0]
M_WALL = [0.93, 0.92, 0.89, 1.0]
M_WALL_TOP = [0.88, 0.90, 0.93, 1.0]  # wainscot upper band
M_BOARD = [0.10, 0.26, 0.20, 1.0]
M_FRAME = [0.28, 0.30, 0.33, 1.0]
M_BASE = [0.82, 0.80, 0.76, 1.0]
M_DESK = [0.58, 0.44, 0.32, 1.0]
M_DESK_TOP = [0.78, 0.68, 0.52, 1.0]
M_CHAIR = [0.22, 0.28, 0.38, 1.0]
M_CHAIR_SEAT = [0.30, 0.36, 0.46, 1.0]
M_CAB = [0.92, 0.42, 0.12, 1.0]  # bright orange — blocking cabinet
M_PODIUM = [0.65, 0.50, 0.38, 1.0]
M_PODIUM_TOP = [0.48, 0.38, 0.30, 1.0]
M_ZONE_OK = [0.22, 0.68, 0.42, 0.28]
M_ZONE_FAIL = [0.92, 0.18, 0.12, 0.35]
M_CEIL = [0.97, 0.97, 0.96, 1.0]
M_LIGHT = [0.98, 0.98, 0.94, 1.0]
M_GLASS = [0.50, 0.68, 0.82, 0.45]
M_EXIT_SIGN = [0.15, 0.75, 0.35, 1.0]
M_EXIT_FAIL = [0.85, 0.15, 0.12, 1.0]


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


def wall_opening_x(meshes, name, z, x0, x1, ox, ow, rgba=M_WALL):
    half = ow / 2
    left, right = ox - half, ox + half
    if left - x0 > 0.05:
        meshes.append(box(f"{name}-L", (x0 + left) / 2, WALL_H / 2, z, left - x0, WALL_H, WALL_T, rgba))
    if x1 - right > 0.05:
        meshes.append(box(f"{name}-R", (right + x1) / 2, WALL_H / 2, z, x1 - right, WALL_H, WALL_T, rgba))
    meshes.append(box(f"{name}-lintel", ox, DOOR_H + LINTEL / 2, z, ow, LINTEL, WALL_T, rgba))


def wall_opening_z(meshes, name, x, z0, z1, oz, ow, rgba=M_WALL):
    half = ow / 2
    a, b = oz - half, oz + half
    if a - z0 > 0.05:
        meshes.append(box(f"{name}-A", x, WALL_H / 2, (z0 + a) / 2, WALL_T, WALL_H, a - z0, rgba))
    if z1 - b > 0.05:
        meshes.append(box(f"{name}-B", x, WALL_H / 2, (b + z1) / 2, WALL_T, WALL_H, z1 - b, rgba))
    meshes.append(box(f"{name}-lintel", x, DOOR_H + LINTEL / 2, oz, WALL_T, LINTEL, ow, rgba))


def add_baseboard(meshes, name, cx, cy, cz, sx, sy, sz):
    meshes.append(box(name, cx, cy, cz, sx, sy, sz, M_BASE))


def add_window(meshes, name, x, z, wall_axis="east"):
    """Framed window: sill + frame + glass."""
    ww, wh = 1.6, 1.35
    cy = 1.55
    if wall_axis == "east":
        meshes.append(box(f"{name}-sill", x - 0.03, 0.72, z, 0.08, 0.06, ww + 0.2, M_FRAME))
        meshes.append(box(f"{name}-frame-T", x - 0.03, cy + wh / 2, z, 0.08, 0.08, ww + 0.16, M_FRAME))
        meshes.append(box(f"{name}-frame-L", x - 0.03, cy, z - ww / 2, 0.08, wh, 0.08, M_FRAME))
        meshes.append(box(f"{name}-frame-R", x - 0.03, cy, z + ww / 2, 0.08, wh, 0.08, M_FRAME))
        meshes.append(box(f"{name}-glass", x - 0.01, cy, z, 0.03, wh - 0.12, ww - 0.12, M_GLASS))
    else:
        meshes.append(box(f"{name}-sill", x, 0.72, z - 0.03, ww + 0.2, 0.06, 0.08, M_FRAME))
        meshes.append(box(f"{name}-frame-T", x, cy + wh / 2, z - 0.03, ww + 0.16, 0.08, 0.08, M_FRAME))
        meshes.append(box(f"{name}-frame-L", x - ww / 2, cy, z - 0.03, 0.08, wh, 0.08, M_FRAME))
        meshes.append(box(f"{name}-frame-R", x + ww / 2, cy, z - 0.03, 0.08, wh, 0.08, M_FRAME))
        meshes.append(box(f"{name}-glass", x, cy, z - 0.01, ww - 0.12, wh - 0.12, 0.03, M_GLASS))


def add_door_leaf(meshes, door_id, cx, cz, width_m, axis, rgba):
    ft = 0.07
    th = 0.05
    if axis == "x":
        meshes.append(box(f"{door_id}-frame-L", cx - width_m / 2, DOOR_H / 2, cz, ft, DOOR_H, 0.14, M_FRAME))
        meshes.append(box(f"{door_id}-frame-R", cx + width_m / 2, DOOR_H / 2, cz, ft, DOOR_H, 0.14, M_FRAME))
        meshes.append(box(f"{door_id}-frame-T", cx, DOOR_H, cz, width_m + 0.04, ft, 0.14, M_FRAME))
        meshes.append(box(door_id, cx, DOOR_H / 2, cz, width_m - 0.06, DOOR_H - 0.06, th, rgba))
    else:
        meshes.append(box(f"{door_id}-frame-L", cx, DOOR_H / 2, cz - width_m / 2, 0.14, DOOR_H, ft, M_FRAME))
        meshes.append(box(f"{door_id}-frame-R", cx, DOOR_H / 2, cz + width_m / 2, 0.14, DOOR_H, ft, M_FRAME))
        meshes.append(box(f"{door_id}-frame-T", cx, DOOR_H, cz, 0.14, ft, width_m + 0.04, M_FRAME))
        meshes.append(box(door_id, cx, DOOR_H / 2, cz, th, DOOR_H - 0.06, width_m - 0.06, rgba))


def add_exit_sign(meshes, door_id, cx, cz, axis, fail=False):
    rgba = M_EXIT_FAIL if fail else M_EXIT_SIGN
    if axis == "x":
        meshes.append(box(f"{door_id}-sign", cx, DOOR_H + 0.25, cz - 0.25, 0.5, 0.12, 0.22, rgba))
    else:
        meshes.append(box(f"{door_id}-sign", cx - 0.25, DOOR_H + 0.25, cz, 0.22, 0.12, 0.5, rgba))


def add_podium(meshes):
    """Raised teaching platform at front of room."""
    px, pz = 6.0, 0.85
    meshes.append(box("Podium-Step1", px, 0.08, pz, 3.2, 0.16, 1.4, M_PODIUM))
    meshes.append(box("Podium-Step2", px, 0.22, pz + 0.15, 2.6, 0.14, 1.0, M_PODIUM))
    meshes.append(box("Podium-Deck", px, 0.36, pz + 0.35, 2.0, 0.08, 0.75, M_PODIUM_TOP))
    meshes.append(box("Podium-Lectern", px + 0.55, 0.62, pz + 0.35, 0.55, 0.52, 0.35, M_PODIUM_TOP))


def add_student_desk(meshes, fid, x, z):
    meshes.append(box(f"{fid}-top", x, 0.76, z, 1.15, 0.05, 0.58, M_DESK_TOP))
    for lx, lz in ((-0.48, -0.22), (0.48, -0.22), (-0.48, 0.22), (0.48, 0.22)):
        meshes.append(box(f"{fid}-leg", x + lx, 0.38, z + lz, 0.05, 0.76, 0.05, M_DESK))
    # chair behind desk
    meshes.append(box(f"{fid}-chair-seat", x, 0.48, z + 0.42, 0.38, 0.06, 0.36, M_CHAIR_SEAT))
    meshes.append(box(f"{fid}-chair-back", x, 0.72, z + 0.58, 0.38, 0.48, 0.06, M_CHAIR))


def add_ceiling_lights(meshes):
    for x in (3.0, 6.0, 9.0):
        for z in (2.5, 5.0, 7.5):
            meshes.append(box(f"Light-{x:.0f}-{z:.0f}", x, WALL_H - 0.08, z, 1.1, 0.06, 0.45, M_LIGHT))


def door_color(door):
    if door["is_exit"] and door["clear_width_mm"] < 900:
        return [0.78, 0.22, 0.18, 1.0]
    if door["is_exit"]:
        return [0.18, 0.52, 0.36, 1.0]
    return [0.40, 0.50, 0.62, 1.0]


def build_semantic_model() -> dict:
    doors = [
        {
            "id": "D-01",
            "name": "Front Exit (West)",
            "is_exit": True,
            "clear_width_mm": 1100,
            "height_mm": 2100,
            "axis": "z",
            "location": {"x": 0.0, "y": 1.6},
            "notes": "Primary classroom exit — compliant width",
        },
        {
            "id": "D-02",
            "name": "Rear Exit (North)",
            "is_exit": True,
            "clear_width_mm": 700,
            "height_mm": 2100,
            "axis": "x",
            "location": {"x": 9.5, "y": 9.0},
            "notes": "Intentional fail: narrow exit + clear-zone clash with cabinet",
        },
        {
            "id": "D-03",
            "name": "Side Exit (East)",
            "is_exit": True,
            "clear_width_mm": 950,
            "height_mm": 2100,
            "axis": "z",
            "location": {"x": 12.0, "y": 4.5},
            "notes": "Secondary exit — compliant",
        },
    ]

    egress_zones = [
        {"id": "EZ-01", "door_id": "D-01", "name": "Clear zone — Front Exit", "aabb": aabb(0.7, 1.6, 1.2, 1.4)},
        {"id": "EZ-02", "door_id": "D-02", "name": "Clear zone — Rear Exit", "aabb": aabb(9.5, 8.25, 1.6, 1.35)},
        {"id": "EZ-03", "door_id": "D-03", "name": "Clear zone — Side Exit", "aabb": aabb(11.3, 4.5, 1.2, 1.4)},
    ]

    furniture = [
        {
            "id": "F-TEACH",
            "name": "Teacher Desk",
            "kind": "desk",
            "aabb": aabb(6.0, 1.55, 1.4, 0.65),
            "center": [6.0, 1.55],
            "size": [1.4, 0.65],
        },
    ]

    desk_id = 1
    for z in (3.0, 4.5, 6.0, 7.5):
        for x in (2.0, 4.2, 7.6):
            furniture.append(
                {
                    "id": f"F-DESK-{desk_id:02d}",
                    "name": f"Student Desk R{desk_id}",
                    "kind": "desk",
                    "aabb": aabb(x, z, 1.15, 0.58),
                    "center": [x, z],
                    "size": [1.15, 0.58],
                }
            )
            desk_id += 1

    # Cabinet squarely in rear exit clear zone
    furniture.append(
        {
            "id": "F-CAB-01",
            "name": "Storage Cabinet (blocking rear exit)",
            "kind": "cabinet",
            "aabb": aabb(9.5, 8.2, 1.15, 0.65),
            "center": [9.5, 8.2],
            "size": [1.15, 0.65],
            "intentional_issue": "Blocks EZ-02 rear exit clear zone",
        }
    )

    return {
        "meta": {
            "name": "Synthetic Classroom — Fire Egress Demo",
            "space_type": "classroom",
            "source": "scripts/generate_sample_classroom.py",
            "units": {"length": "meter", "door_width": "millimeter"},
            "formats": ["json", "gltf", "ifc"],
            "rules_targeted": [
                "R1 exit door clear_width_mm >= 900",
                "R2 furniture AABB must not intersect exit egress clear zones",
            ],
            "disclaimer": "Synthetic academic demo only. Not company project data.",
        },
        "building": {
            "id": "B-CR-01",
            "name": "Demo Classroom CR-101",
            "storey": "L2",
            "footprint_m": {"width": ROOM_W, "depth": ROOM_D, "height": WALL_H},
        },
        "doors": doors,
        "egress_zones": egress_zones,
        "furniture": furniture,
    }


def build_meshes(model: dict) -> list[dict]:
    meshes: list[dict] = []
    doors = {d["id"]: d for d in model["doors"]}

    # Floor + centre aisle strip
    meshes.append(box("Floor", ROOM_W / 2, -0.04, ROOM_D / 2, ROOM_W + 0.2, 0.08, ROOM_D + 0.2, M_FLOOR))
    meshes.append(box("Aisle-Center", 6.0, -0.02, 5.0, 1.4, 0.02, ROOM_D - 1.2, M_AISLE))
    meshes.append(box("Ceiling", ROOM_W / 2, WALL_H + 0.04, ROOM_D / 2, ROOM_W, 0.05, ROOM_D, M_CEIL))
    add_ceiling_lights(meshes)

    # Wainscot band (lower wall colour)
    for seg, cx, cz, sx, sz in (
        ("Front", ROOM_W / 2, 0.0, ROOM_W, WALL_T),
        ("Back-L", 4.0, ROOM_D, 8.0, WALL_T),
        ("Back-R", 11.0, ROOM_D, 2.0, WALL_T),
        ("West", 0.0, ROOM_D / 2, WALL_T, ROOM_D),
        ("East", ROOM_W, ROOM_D / 2, WALL_T, ROOM_D),
    ):
        meshes.append(box(f"Wainscot-{seg}", cx, 1.0, cz, sx, 2.0, sz, M_WALL_TOP))

    # Front wall + blackboard
    meshes.append(box("Wall-Front", ROOM_W / 2, WALL_H / 2, 0.0, ROOM_W, WALL_H, WALL_T, M_WALL))
    meshes.append(box("Blackboard", ROOM_W / 2, 1.75, 0.09, 6.0, 1.55, 0.05, M_BOARD))
    meshes.append(box("Board-Chalk-Ledge", ROOM_W / 2, 0.92, 0.14, 6.0, 0.08, 0.12, M_FRAME))
    meshes.append(box("Board-Frame-L", 3.05, 1.75, 0.10, 0.06, 1.55, 0.06, M_FRAME))
    meshes.append(box("Board-Frame-R", 8.95, 1.75, 0.10, 0.06, 1.55, 0.06, M_FRAME))

    # Back wall with rear exit
    d2 = doors["D-02"]
    w2 = d2["clear_width_mm"] / 1000
    wall_opening_x(meshes, "Wall-Back", ROOM_D, 0.0, ROOM_W, d2["location"]["x"], w2 + 0.12)

    d1 = doors["D-01"]
    w1 = d1["clear_width_mm"] / 1000
    wall_opening_z(meshes, "Wall-West", 0.0, 0.0, ROOM_D, d1["location"]["y"], w1 + 0.12)

    d3 = doors["D-03"]
    w3 = d3["clear_width_mm"] / 1000
    wall_opening_z(meshes, "Wall-East", ROOM_W, 0.0, ROOM_D, d3["location"]["y"], w3 + 0.12)

    add_window(meshes, "Win-East-1", ROOM_W, 2.2)
    add_window(meshes, "Win-East-2", ROOM_W, 6.8)

    # Baseboards
    add_baseboard(meshes, "Base-Front", ROOM_W / 2, BASE_H / 2, 0.12, ROOM_W - 0.3, BASE_H, 0.06)
    add_baseboard(meshes, "Base-Back", ROOM_W / 2, BASE_H / 2, ROOM_D - 0.12, ROOM_W - 0.3, BASE_H, 0.06)
    add_baseboard(meshes, "Base-West", 0.12, BASE_H / 2, ROOM_D / 2, 0.06, BASE_H, ROOM_D - 0.3)
    add_baseboard(meshes, "Base-East", ROOM_W - 0.12, BASE_H / 2, ROOM_D / 2, 0.06, BASE_H, ROOM_D - 0.3)

    add_podium(meshes)

    # Teacher desk on podium deck area
    meshes.append(box("F-TEACH", 6.0, 0.52, 1.55, 1.4, 0.76, 0.65, M_DESK))
    meshes.append(box("F-TEACH-top", 6.0, 0.92, 1.55, 1.45, 0.04, 0.7, M_DESK_TOP))

    desk_id = 1
    for z in (3.0, 4.5, 6.0, 7.5):
        for x in (2.0, 4.2, 7.6):
            add_student_desk(meshes, f"F-DESK-{desk_id:02d}", x, z)
            desk_id += 1

    # Blocking cabinet — tall, bright, directly in rear clear zone
    meshes.append(box("F-CAB-01", 9.5, 1.05, 8.2, 1.15, 2.1, 0.65, M_CAB))
    meshes.append(box("F-CAB-01-handle", 9.5, 1.0, 7.92, 0.04, 0.25, 0.04, M_FRAME))

    for d in model["doors"]:
        add_door_leaf(
            meshes,
            d["id"],
            d["location"]["x"],
            d["location"]["y"],
            d["clear_width_mm"] / 1000,
            d["axis"],
            door_color(d),
        )
        add_exit_sign(
            meshes,
            d["id"],
            d["location"]["x"],
            d["location"]["y"],
            d["axis"],
            fail=d["id"] == "D-02",
        )

    # Egress zones — raised slightly, EZ-02 brighter red
    for z in model["egress_zones"]:
        mn, mx = z["aabb"]["min"], z["aabb"]["max"]
        cx, cz = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
        sx, sz = mx[0] - mn[0], mx[1] - mn[1]
        rgba = M_ZONE_FAIL if z["id"] == "EZ-02" else M_ZONE_OK
        meshes.append(box(z["id"], cx, 0.06, cz, sx, 0.12, sz, rgba))
        # zone border outline
        border = 0.04
        for bx, bz, bsx, bsz in (
            (cx, cz - sz / 2 + border / 2, sx, border),
            (cx, cz + sz / 2 - border / 2, sx, border),
            (cx - sx / 2 + border / 2, cz, border, sz),
            (cx + sx / 2 - border / 2, cz, border, sz),
        ):
            meshes.append(box(f"{z['id']}-edge", bx, 0.10, bz, bsx, 0.04, bsz, rgba[:3] + [0.7]))

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
                "metallicFactor": 0.04,
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
        "asset": {"version": "2.0", "generator": "generate_sample_classroom.py"},
        "scene": 0,
        "scenes": [{"name": "Classroom", "nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": gltf_meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(blob), "uri": "sample_classroom.bin"}],
    }
    path.write_text(json.dumps(gltf, indent=2), encoding="utf-8")
    path.with_suffix(".bin").write_bytes(blob)


def write_minimal_ifc(model: dict, path: Path) -> None:
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');",
        "FILE_NAME('sample_classroom.ifc','2026-07-21T00:00:00',('Lu Yu'),('HKU AI+BIM demo'),"
        "'generate_sample_classroom.py','generate_sample_classroom.py','');",
        "FILE_SCHEMA(('IFC4'));",
        "ENDSEC;",
        "DATA;",
        "#1=IFCPERSON($,$,'Demo',$,$,$,$,$);",
        "#2=IFCORGANIZATION($,'Synthetic Classroom Demo',$,$,$);",
        "#3=IFCPERSONANDORGANIZATION(#1,#2,$);",
        "#4=IFCAPPLICATION(#2,'0.1','Classroom Fire Egress Demo','CRDemo');",
        "#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,$,$,0);",
        "#6=IFCCARTESIANPOINT((0.,0.,0.));",
        "#7=IFCDIRECTION((0.,0.,1.));",
        "#8=IFCDIRECTION((1.,0.,0.));",
        "#9=IFCAXIS2PLACEMENT3D(#6,#7,#8);",
        "#10=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.0E-5,#9,$);",
        "#12=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);",
        "#13=IFCUNITASSIGNMENT((#12));",
        "#14=IFCPROJECT('2ProjectClassroom00001',#5,'Classroom Fire Demo',$,$,$,$,(#10),#13);",
        "#20=IFCCARTESIANPOINT((0.,0.,0.));",
        "#21=IFCAXIS2PLACEMENT3D(#20,#7,#8);",
        "#22=IFCLOCALPLACEMENT($,#21);",
        "#23=IFCSITE('2SiteClassroom0000001',#5,'Site',$,$,#22,$,$,.ELEMENT.,$,$,0.,$,$);",
        "#24=IFCRELAGGREGATES('2RelAggProject0000001',#5,$,$,#14,(#23));",
        "#30=IFCCARTESIANPOINT((0.,0.,0.));",
        "#31=IFCAXIS2PLACEMENT3D(#30,#7,#8);",
        "#32=IFCLOCALPLACEMENT(#22,#31);",
        "#33=IFCBUILDING('2BuildingClassroom001',#5,'School Wing',$,$,#32,$,$,.ELEMENT.,$,$,$);",
        "#34=IFCRELAGGREGATES('2RelAggSite000000001',#5,$,$,#23,(#33));",
        "#40=IFCCARTESIANPOINT((0.,0.,0.));",
        "#41=IFCAXIS2PLACEMENT3D(#40,#7,#8);",
        "#42=IFCLOCALPLACEMENT(#32,#41);",
        "#43=IFCBUILDINGSTOREY('2StoreyClassroom0001',#5,'L2',$,$,#42,$,$,.ELEMENT.,0.);",
        "#44=IFCRELAGGREGATES('2RelAggBldg000000001',#5,$,$,#33,(#43));",
        "#50=IFCSPACE('2SpaceClassroom00001',#5,'CR-101','Classroom',$,#42,$,'CR-101',.ELEMENT.,.INTERNAL.,$);",
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
    model = build_semantic_model()
    (DATA / "sample_classroom.json").write_text(
        json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    meshes = build_meshes(model)
    write_gltf(meshes, DATA / "sample_classroom.gltf")
    write_minimal_ifc(model, DATA / "sample_classroom.ifc")
    print(f"meshes: {len(meshes)}")
    for d in model["doors"]:
        flag = "FAIL_WIDTH" if d["clear_width_mm"] < 900 else "ok"
        print(f"  {d['id']}: {d['clear_width_mm']}mm [{flag}]")
    print("  F-CAB-01 blocks EZ-02 (R2 clash)")


if __name__ == "__main__":
    main()
