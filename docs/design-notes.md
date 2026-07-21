# Design notes — HK high-rise residential egress

## Motivation (respectful framing)

Recent tragedies and public inquiries in Hong Kong have renewed debate on **high-rise residential fire safety**: escape routes, fire-rated doors, corridor occupation, and whether design + management fail under emergency conditions.

This micro-prototype is **not** a reconstruction of any specific building or incident. It models a **synthetic typical floor corridor** to demonstrate how two checkable failure modes can be flagged early:

| Mode | Demo rule | Real-world concern |
|------|-----------|-------------------|
| Undersized stair door | R1: clear width ≥ 900 mm | Egress capacity / compliance |
| Blocked stair landing | R2: no obstruction in clear zone | Strollers, cartons, refuse blocking escape path |

Broader topics (facade renovation fire spread, compartmentation breakdown) are noted as **future work** — intentionally out of scope for a 7-day, 2-rule demo.

## HK architectural cues in the model

- Long narrow **typical floor corridor** (common in public / private towers)
- **Lift bank** mid-run
- Multiple **flat entrance doors** on one side
- **Fire stair doors** with exit signage
- **Hose reel** cabinet
- Corridor **occupation objects** (stroller, renovation cartons)

## IFC mapping

- `doors[].clear_width_mm` → `IfcDoor.OverallWidth`
- Obstructions + clear zones live in JSON AABBs for transparent, testable rules

## Human–AI loop

Deterministic rules decide pass/fail. AI (`prompts/` or `explain.py`) narrates fixes — it does not invent compliance verdicts.
