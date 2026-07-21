from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


EXIT_CLEAR_WIDTH_MM = 900


@dataclass
class Finding:
    rule_id: str
    severity: str  # "fail" | "warn" | "pass"
    element_type: str
    element_id: str
    element_name: str
    message: str
    measured: dict[str, Any]
    expected: dict[str, Any]


@dataclass
class CheckResult:
    summary: dict[str, int]
    findings: list[Finding]
    meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "findings": [asdict(f) for f in self.findings],
            "meta": self.meta,
        }


def _aabb_overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Axis-aligned overlap in plan (x/z). Touching edges count as overlap."""
    amin, amax = a["min"], a["max"]
    bmin, bmax = b["min"], b["max"]
    return not (amax[0] < bmin[0] or bmax[0] < amin[0] or amax[1] < bmin[1] or bmax[1] < amin[1])


def _overlap_area(a: dict[str, Any], b: dict[str, Any]) -> float:
    if not _aabb_overlap(a, b):
        return 0.0
    x0 = max(a["min"][0], b["min"][0])
    x1 = min(a["max"][0], b["max"][0])
    z0 = max(a["min"][1], b["min"][1])
    z1 = min(a["max"][1], b["max"][1])
    return max(0.0, x1 - x0) * max(0.0, z1 - z0)


EXIT_CLEAR_WIDTH_MM = 900  # default; overridden by model.meta.rule_config


def get_rule_config(model: dict[str, Any]) -> dict[str, Any]:
    cfg = (model.get("meta") or {}).get("rule_config") or {}
    return {
        "exit_clear_width_mm_min": int(cfg.get("exit_clear_width_mm_min", EXIT_CLEAR_WIDTH_MM)),
        "width_semantics": cfg.get("width_semantics", "clear_width_mm"),
        "width_semantics_note": cfg.get(
            "width_semantics_note",
            "JSON field clear_width_mm = net clear width after frame; not gross opening.",
        ),
        "jurisdiction_note": cfg.get(
            "jurisdiction_note",
            "Demo threshold — configure per project / code set (e.g. 1200 mm primary exits).",
        ),
    }


def _check_exit_door_width(door: dict[str, Any], cfg: dict[str, Any]) -> Finding | None:
    if not door.get("is_exit"):
        return None
    min_w = cfg["exit_clear_width_mm_min"]
    width = int(door.get("clear_width_mm") or 0)
    ok = width >= min_w
    sem = cfg["width_semantics"]
    return Finding(
        rule_id="R1_EXIT_CLEAR_WIDTH",
        severity="pass" if ok else "fail",
        element_type="door",
        element_id=door["id"],
        element_name=door.get("name") or door["id"],
        message=(
            f"Exit door {sem} {width} mm meets minimum {min_w} mm."
            if ok
            else f"Exit door {sem} {width} mm is below minimum {min_w} mm."
        ),
        measured={"clear_width_mm": width, "width_semantics": sem, "is_exit": True},
        expected={"clear_width_mm_min": min_w, "width_semantics": sem},
    )


def _check_egress_clashes(model: dict[str, Any]) -> list[Finding]:
    """
    R2: fire-egress clash — furniture must not intersect exit clear zones.
    This is a simplified geometric proxy for keeping the escape path free.
    """
    findings: list[Finding] = []
    zones = model.get("egress_zones", [])
    furniture = model.get("furniture", [])
    door_by_id = {d["id"]: d for d in model.get("doors", [])}

    clash_count = 0
    for zone in zones:
        zone_aabb = zone["aabb"]
        door = door_by_id.get(zone.get("door_id"), {})
        hits = []
        for furn in furniture:
            area = _overlap_area(zone_aabb, furn["aabb"])
            if area > 1e-6:
                hits.append((furn, area))
                clash_count += 1
                findings.append(
                    Finding(
                        rule_id="R2_EGRESS_ZONE_CLASH",
                        severity="fail",
                        element_type="furniture",
                        element_id=furn["id"],
                        element_name=furn.get("name") or furn["id"],
                        message=(
                            f"{furn.get('name', furn['id'])} clashes with {zone.get('name', zone['id'])} "
                            f"(overlap ~ {area:.2f} m2) — blocks fire egress clear space at "
                            f"{door.get('name', zone.get('door_id', 'exit'))}."
                        ),
                        measured={
                            "overlap_m2": round(area, 3),
                            "furniture_aabb": furn["aabb"],
                            "egress_zone_id": zone["id"],
                            "door_id": zone.get("door_id"),
                        },
                        expected={"overlap_m2_max": 0.0, "keep_exit_clear_zone_free": True},
                    )
                )
        if not hits:
            findings.append(
                Finding(
                    rule_id="R2_EGRESS_ZONE_CLASH",
                    severity="pass",
                    element_type="egress_zone",
                    element_id=zone["id"],
                    element_name=zone.get("name") or zone["id"],
                    message=f"{zone.get('name', zone['id'])} is clear of furniture.",
                    measured={"overlap_m2": 0.0, "door_id": zone.get("door_id")},
                    expected={"overlap_m2_max": 0.0},
                )
            )

    return findings


def run_checks(model: dict[str, Any]) -> CheckResult:
    cfg = get_rule_config(model)
    min_w = cfg["exit_clear_width_mm_min"]
    findings: list[Finding] = []

    for door in model.get("doors", []):
        width_finding = _check_exit_door_width(door, cfg)
        if width_finding is not None:
            findings.append(width_finding)

    findings.extend(_check_egress_clashes(model))

    summary = {
        "pass": sum(1 for f in findings if f.severity == "pass"),
        "warn": sum(1 for f in findings if f.severity == "warn"),
        "fail": sum(1 for f in findings if f.severity == "fail"),
        "total": len(findings),
    }

    return CheckResult(
        summary=summary,
        findings=findings,
        meta={
            "model_name": (model.get("meta") or {}).get("name"),
            "space_type": (model.get("meta") or {}).get("space_type"),
            "rule_config": cfg,
            "rules": [
                {
                    "id": "R1_EXIT_CLEAR_WIDTH",
                    "description": f"Exit door {cfg['width_semantics']} >= {min_w} mm",
                },
                {
                    "id": "R2_EGRESS_ZONE_CLASH",
                    "description": "Plan AABB overlap: furniture vs stair landing clear zone (2D geometric check)",
                },
            ],
            "scope_note": (
                "7-day micro-prototype: synthetic JSON + plan AABB geometry. "
                "Not a production IFC solid-clash engine. See docs/limitations-and-scope.md."
            ),
            "design_note": (
                "Deterministic rules decide pass/fail; AI (prompts/ + explain.py) only explains."
            ),
        },
    )
