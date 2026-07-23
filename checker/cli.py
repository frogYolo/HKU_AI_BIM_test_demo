"""CLI: python -m checker.cli [path/to/model.json]"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from checker.explain import explain_findings
from checker.rules import run_checks

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "sample_hk_tower_floor.json"
    model = json.loads(path.read_text(encoding="utf-8"))
    result = run_checks(model).to_dict()
    result["explanation"] = explain_findings(result, model=model)
    # Windows consoles may be GBK; ASCII-safe dump keeps CLI usable without UTF-8 setup.
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
