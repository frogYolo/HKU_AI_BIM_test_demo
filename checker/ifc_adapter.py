"""Minimal IFC → JSON door adapter (no ifcopenshell required).

Demo scope:
- Parses IFCDOOR OverallWidth / Tag / Name from STEP text
- Merges widths into an existing JSON model schema used by checker/rules.py
- Does NOT resolve full geometry, property sets, or clear-vs-gross deductions

Production path: replace this stub with ifcopenshell + project property mapping.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

# Capture Name, Tag, and the remaining attribute list (schema variants differ).
_IFCDOOR_RE = re.compile(
    r"IFCDOOR\(\s*"
    r"'[^']*'\s*,\s*"  # GlobalId
    r"[^,]*,\s*"  # OwnerHistory
    r"(?:'([^']*)'|\$)\s*,\s*"  # Name
    r"(?:'[^']*'|\$)\s*,\s*"  # Description
    r"[^,]*,\s*"  # ObjectType
    r"[^,]*,\s*"  # ObjectPlacement
    r"[^,]*,\s*"  # Representation
    r"(?:'([^']*)'|\$)\s*,\s*"  # Tag
    r"([^)]*)\)",  # remaining attrs (height/width/enums — order varies)
    re.IGNORECASE,
)


def _overall_width_mm(rest_attrs: str) -> int | None:
    """
    Take the first two numeric literals after Tag as OverallHeight, OverallWidth (metres).

    Handles both:
    - IFC4-ish: Tag, OverallHeight, OverallWidth, ...
    - This demo file: Tag, .DOOR., OverallHeight, OverallWidth, ...
    """
    nums = re.findall(r"([0-9]+(?:\.[0-9]+)?)", rest_attrs)
    if len(nums) < 2:
        return None
    return int(round(float(nums[1]) * 1000))


def extract_doors_from_ifc_text(ifc_text: str) -> list[dict[str, Any]]:
    """Return door dicts compatible with the demo JSON `doors[]` schema."""
    doors: list[dict[str, Any]] = []
    for match in _IFCDOOR_RE.finditer(ifc_text):
        name, tag, rest = match.groups()
        door_id = (tag or name or "").strip()
        if not door_id:
            continue
        width_mm = _overall_width_mm(rest)
        if width_mm is None:
            continue
        doors.append(
            {
                "id": door_id,
                "name": name or door_id,
                "is_exit": True,
                "clear_width_mm": width_mm,
                "source": "ifc_overall_width_m_x1000",
                "notes": (
                    "Width taken from IfcDoor.OverallWidth (metres to mm). "
                    "Treat as gross unless project mapping deducts frame/hardware."
                ),
            }
        )
    return doors


def extract_doors_from_ifc(path: str | Path) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return extract_doors_from_ifc_text(text)


def merge_ifc_doors_into_model(
    base_model: dict[str, Any],
    ifc_path: str | Path,
) -> dict[str, Any]:
    """
    Clone `base_model` and overwrite matching `doors[]` clear_width_mm from IFC.

    Unmatched IFC doors are appended. Non-door fields (zones, furniture) stay
    from the JSON base — this demo IFC has no furniture geometry.
    """
    model = copy.deepcopy(base_model)
    ifc_doors = extract_doors_from_ifc(ifc_path)
    by_id = {d["id"]: d for d in model.get("doors", [])}

    for src in ifc_doors:
        if src["id"] in by_id:
            by_id[src["id"]]["clear_width_mm"] = src["clear_width_mm"]
            by_id[src["id"]]["name"] = src.get("name") or by_id[src["id"]].get("name")
            notes = by_id[src["id"]].get("notes") or ""
            by_id[src["id"]]["notes"] = (notes + " | " if notes else "") + src["notes"]
            by_id[src["id"]]["source"] = src["source"]
        else:
            by_id[src["id"]] = src

    model["doors"] = list(by_id.values())
    meta = model.setdefault("meta", {})
    meta["ifc_adapter"] = {
        "path": str(ifc_path),
        "doors_imported": len(ifc_doors),
        "note": "Stub adapter: OverallWidth only. Not a full ifcopenshell pipeline.",
    }
    return model
