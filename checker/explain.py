from __future__ import annotations

from typing import Any


def explain_findings(result: dict[str, Any]) -> dict[str, Any]:
    fails = [f for f in result["findings"] if f["severity"] == "fail"]
    warns = [f for f in result["findings"] if f["severity"] == "warn"]

    actions: list[str] = []
    for f in fails:
        if f["rule_id"] == "R1_EXIT_CLEAR_WIDTH":
            need = f["expected"]["clear_width_mm_min"]
            got = f["measured"]["clear_width_mm"]
            actions.append(
                f"Upgrade fire stair door {f['element_id']} ({f['element_name']}) "
                f"from {got} mm to >= {need} mm clear width."
            )
        elif f["rule_id"] == "R2_EGRESS_ZONE_CLASH":
            zone = f["measured"].get("egress_zone_id", "stair landing zone")
            door = f["measured"].get("door_id", "fire stair")
            actions.append(
                f"Remove {f['element_id']} ({f['element_name']}) from {zone} at {door}. "
                f"Keep stair landings free of strollers, cartons, and storage."
            )

    if not actions:
        narrative = "Fire stair widths and landing clear zones look acceptable for this demo rule set."
    else:
        narrative = (
            f"Found {len(fails)} high-rise egress issue(s)"
            + (f" and {len(warns)} warning(s)" if warns else "")
            + ". In emergencies, blocked landings and narrow stair doors compound evacuation risk — "
            "fix obstructions first, then door widths."
        )

    return {
        "mode": "deterministic_agent",
        "narrative": narrative,
        "recommended_actions": actions,
        "human_ai_loop": [
            "Human sets HK corridor egress criteria (900 mm stair doors, clear landings).",
            "Tool runs deterministic width + AABB clash checks on synthetic floor data.",
            "Agent explains findings for managers / designers.",
            "Human validates on site and updates the model or building management practice.",
        ],
    }
