from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from checker.explain import explain_findings
from checker.rules import run_checks

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
WEB = ROOT / "web"
SAMPLE = DATA / "sample_hk_tower_floor.json"

app = FastAPI(
    title="HK Tower Corridor Fire Egress Demo",
    description="Fire stair door width + landing obstruction checks on a synthetic HK residential floor.",
    version="0.3.0",
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/sample")
def sample_model():
    if not SAMPLE.exists():
        raise HTTPException(404, "Sample missing. Run scripts/generate_sample_hk_tower_floor.py")
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


@app.get("/api/check")
def check_sample_get():
    model = sample_model()
    result = run_checks(model).to_dict()
    result["explanation"] = explain_findings(result)
    result["model"] = model
    return result


@app.post("/api/check")
async def check_model(file: UploadFile | None = File(None)):
    if file is not None and file.filename:
        raw = await file.read()
        try:
            model = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"Invalid JSON: {exc}") from exc
    else:
        model = sample_model()

    result = run_checks(model).to_dict()
    result["explanation"] = explain_findings(result)
    result["model"] = model
    return result


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/data", StaticFiles(directory=str(DATA)), name="data")
app.mount("/static", StaticFiles(directory=str(WEB)), name="static")
