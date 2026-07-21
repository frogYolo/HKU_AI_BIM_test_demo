from __future__ import annotations

import json
import os
from typing import Any


def _default_human_ai_loop() -> list[str]:
    return [
        "Human sets HK corridor egress criteria (e.g., 900 mm stair doors, clear landings).",
        "Tool runs deterministic width + 2D AABB overlap checks on synthetic floor data.",
        "Agent explains findings for managers / designers.",
        "Human validates on site and updates the model or building management practice.",
    ]


def _deterministic_explanation(result: dict[str, Any]) -> dict[str, Any]:
    findings = list(result.get("findings", []))
    fails = [f for f in findings if f.get("severity") == "fail"]
    warns = [f for f in findings if f.get("severity") == "warn"]

    r2_fails = [f for f in fails if f.get("rule_id") == "R2_EGRESS_ZONE_CLASH"]
    r1_fails = [f for f in fails if f.get("rule_id") == "R1_EXIT_CLEAR_WIDTH"]

    def _fmt_float(x: Any, digits: int = 2) -> str:
        try:
            return f"{float(x):.{digits}f}"
        except Exception:
            return str(x)

    actions: list[str] = []

    # Priority: landings first (R2), then door widths (R1)
    for f in r2_fails:
        zone = f.get("measured", {}).get("egress_zone_id", "stair landing zone")
        door = f.get("measured", {}).get("door_id", "fire stair")
        overlap_m2 = f.get("measured", {}).get("overlap_m2", None)
        overlap_str = ""
        if overlap_m2 is not None:
            overlap_str = f" (overlap ~ {_fmt_float(overlap_m2)} m²)"
        actions.append(
            f"Remove {f['element_id']} ({f.get('element_name', f['element_id'])}) from {zone} at {door}."
            f" Keep the stair landing clear of strollers, cartons, and storage{overlap_str}."
        )

    for f in r1_fails:
        need = f.get("expected", {}).get("clear_width_mm_min", "900")
        got = f.get("measured", {}).get("clear_width_mm", "0")
        actions.append(
            f"Upgrade fire stair door {f['element_id']} ({f.get('element_name', f['element_id'])})"
            f" from {got} mm to >= {need} mm clear width."
        )

    if not fails:
        narrative = "All checked egress items pass this demo rule set."
    else:
        blocked_zone_ids = sorted({f.get("measured", {}).get("egress_zone_id", "stair landing zone") for f in r2_fails})
        blocked_items = len(r2_fails)
        narrow_doors = len(r1_fails)
        door_details = []
        for f in r1_fails:
            got = f.get("measured", {}).get("clear_width_mm", "?")
            need = f.get("expected", {}).get("clear_width_mm_min", "?")
            door_details.append(f"{f['element_id']} = {got} mm (min {need} mm)")

        narrative = (
            f"Detected {len(blocked_zone_ids)} stair landing clear zone(s) blocked by {blocked_items} obstruction(s) (R2)."
            if blocked_items
            else "No R2 landing obstructions were detected."
        )
        if narrow_doors:
            narrative += f" Also found {narrow_doors} undersized fire stair door(s) (R1): " + ", ".join(door_details) + "."
        else:
            narrative += " Fire stair door widths meet the R1 threshold for this demo."
        if warns:
            narrative += f" Additionally, {len(warns)} warning(s) were reported (non-blocking under this demo set)."

    human_follow_up: list[str] = []
    if r2_fails:
        human_follow_up.append(
            "Has occupation (e.g., strollers/cartons) been verified as absent from the stair landing clear zones during peak times?"
        )
    if r1_fails:
        human_follow_up.append(
            "Does the measured fire-stair clear width represent the net clear opening after frame/door hardware?"
        )
    human_follow_up = human_follow_up[:2]

    return {
        "mode": "deterministic_agent",
        "narrative": narrative,
        "recommended_actions": actions,
        "human_ai_loop": _default_human_ai_loop(),
        "human_follow_up": human_follow_up,
    }


def _llm_explanation(result: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("openai package is not installed") from exc

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    system_prompt = (
        "You are a BIM fire-egress explanation assistant. "
        "The compliance verdicts are deterministic and already decided. "
        "Do not invent or alter findings/severity/rules. "
        "Return only a JSON object with keys: narrative, recommended_actions, human_follow_up."
    )
    user_prompt = (
        "Analyze the deterministic check result below and explain it in concise professional language.\n"
        "Priority: blocked stair landing clashes (R2) first, then undersized stair doors (R1).\n"
        "Constraints:\n"
        "- narrative <= 80 words\n"
        "- recommended_actions: one concise action per fail item\n"
        "- human_follow_up: max 2 practical questions\n\n"
        f"CHECK_RESULT_JSON:\n{json.dumps(result, ensure_ascii=False)}"
    )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content or "{}"
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise RuntimeError("LLM response is not a JSON object")

    narrative = payload.get("narrative", "")
    if not isinstance(narrative, str):
        narrative = str(narrative)

    recommended_actions_raw = payload.get("recommended_actions", [])
    if not isinstance(recommended_actions_raw, list):
        recommended_actions_raw = [str(recommended_actions_raw)]
    recommended_actions = [str(x) for x in recommended_actions_raw if str(x).strip()]

    follow_up_raw = payload.get("human_follow_up", [])
    if not isinstance(follow_up_raw, list):
        follow_up_raw = [str(follow_up_raw)]
    human_follow_up = [str(x) for x in follow_up_raw if str(x).strip()][:2]

    return {
        "mode": "llm_agent",
        "narrative": narrative,
        "recommended_actions": recommended_actions,
        "human_ai_loop": _default_human_ai_loop(),
        "human_follow_up": human_follow_up,
        "llm_model": model,
    }


def explain_findings(result: dict[str, Any]) -> dict[str, Any]:
    mode = os.getenv("EXPLAIN_MODE", "deterministic").strip().lower()
    deterministic = _deterministic_explanation(result)

    # Save tokens when no issues are present.
    findings = list(result.get("findings", []))
    has_issue = any(f.get("severity") in {"fail", "warn"} for f in findings)
    if mode != "llm" or not has_issue:
        return deterministic

    try:
        return _llm_explanation(result)
    except Exception as exc:  # noqa: BLE001
        fallback = dict(deterministic)
        fallback["mode"] = "deterministic_agent_fallback"
        fallback["fallback_reason"] = str(exc)
        return fallback
