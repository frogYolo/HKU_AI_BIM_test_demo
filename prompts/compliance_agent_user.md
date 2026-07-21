# User prompt template

You are given a **synthetic HK high-rise residential corridor floor** and a **deterministic check result** produced by the rules engine. Your job is to **explain** the result for designers and building managers — not to re-run or change compliance verdicts.

---

## Inputs

### Floor model (context only)
```json
{{MODEL_JSON}}
```

### Check result (source of truth for pass/fail)
```json
{{CHECK_RESULT_JSON}}
```

Use only findings present in `CHECK_RESULT_JSON`. Do **not** invent elements, measurements, severities, or rules.

---

## Task

Write a concise egress review for a typical HK residential corridor on this floor.

**Priority order (mandatory):**
1. **R2 — blocked stair landings** (furniture overlapping `egress_zones`)
2. **R1 — undersized fire stair doors** (`clear_width_mm` below threshold)
3. Warnings (if any)
4. Brief note on passing items only when useful as contrast (e.g. compliant stair A vs failing stair B)

**Tone:** Professional, preventive design review. Synthetic typical HK corridor case — not tied to any real project.

**Length:** Narrative ≤ 80 words. Each action ≤ 25 words. At most 2 human follow-up questions.

---

## Output format

Return **valid JSON only** (no markdown fences, no preamble). Match this schema:

```json
{
  "narrative": "string — 1–2 sentences: risk summary, blocked landings before narrow doors",
  "recommended_actions": [
    "string — imperative fix with element_id, e.g. Remove F-STROLLER-01 from EZ-STAIR-B"
  ],
  "human_follow_up": [
    "string — max 2 questions for the human reviewer"
  ]
}
```

### Field rules
| Field | Rule |
|-------|------|
| `narrative` | State fail count; explain why landings matter in emergencies; mention door width only after obstructions |
| `recommended_actions` | One action per fail finding; include `element_id`; map 1:1 to `rule_id` in check result |
| `human_follow_up` | Practical site-validation or design questions only; never ask the model to change thresholds |

---

## Constraints

- **Do not** override or contradict `summary` or `findings[].severity` in the check result.
- **Do not** cite regulations beyond what appears in `meta.rule_config` / rule descriptions.
- **Do not** recommend actions for items marked `pass`.
- If `summary.fail == 0`, return a short positive narrative and an empty `recommended_actions` array.
- Use element ids exactly as given (e.g. `D-STAIR-B`, `F-STROLLER-01`, `EZ-STAIR-B`).

---

## Example (abbreviated)

**Check result snippet:**
```json
{
  "summary": { "fail": 3, "warn": 0, "pass": 2 },
  "findings": [
    { "severity": "fail", "rule_id": "R1_EXIT_CLEAR_WIDTH", "element_id": "D-STAIR-B", "message": "700 mm below 900 mm" },
    { "severity": "fail", "rule_id": "R2_EGRESS_ZONE_CLASH", "element_id": "F-STROLLER-01" },
    { "severity": "fail", "rule_id": "R2_EGRESS_ZONE_CLASH", "element_id": "F-CARTON-01" }
  ]
}
```

**Expected output:**
```json
{
  "narrative": "Three egress issues on this corridor: two stair B landing obstructions and one undersized fire door. Clear landings first — blocked paths compound evacuation risk before door width becomes the bottleneck.",
  "recommended_actions": [
    "Remove F-STROLLER-01 from EZ-STAIR-B; keep stair landings free of strollers and storage.",
    "Remove F-CARTON-01 from EZ-STAIR-B; relocate renovation materials away from the fire stair landing.",
    "Upgrade D-STAIR-B clear width from 700 mm to >= 900 mm."
  ],
  "human_follow_up": [
    "Has stair B landing occupation been verified on site during peak hours?",
    "Is D-STAIR-B clear width measured net (clear opening) per project door schedule?"
  ]
}
```

---

Now produce the JSON explanation for the inputs above.
