import argparse
import os
from pathlib import Path

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .. import config
from ..storage import db
from ..hooks.activations import from_arrays as activations_from_arrays
from ..methods.gradcam import from_arrays as gradcam_from_arrays
from ..methods.shap_explain import from_arrays as shap_from_arrays

app = FastAPI(title="LensNN Viewer")
_state = {"runs_dir": config.RUNS_DIR}


def set_runs_dir(runs_dir):
    _state["runs_dir"] = runs_dir


def _db_path():
    return db.default_db_path(_state["runs_dir"])


def _load_npz(npz_path):
    with np.load(npz_path, allow_pickle=False) as npz:
        return {key: npz[key] for key in npz.files}


def _get_capture_or_404(capture_id):
    capture = db.get_capture(_db_path(), capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="capture not found")
    return capture


@app.get("/api/runs")
def get_runs():
    return db.list_runs(_db_path())


@app.get("/api/runs/{run_id}/captures")
def get_captures(run_id: str):
    return db.list_captures(_db_path(), run_id)


@app.get("/api/captures/{capture_id}/activations")
def get_activations(capture_id: str):
    capture = _get_capture_or_404(capture_id)
    if not os.path.exists(capture["npz_path"]):
        return {}
    return activations_from_arrays(_load_npz(capture["npz_path"]))


@app.get("/api/captures/{capture_id}/gradcam")
def get_gradcam(capture_id: str):
    capture = _get_capture_or_404(capture_id)
    if not os.path.exists(capture["npz_path"]):
        return {"available": False}

    result = gradcam_from_arrays(_load_npz(capture["npz_path"]))
    if result is None:
        return {"available": False}

    return {
        "available": True,
        "layer_name": result["layer_name"],
        "heatmaps": result["heatmaps"].tolist(),
        "sample_inputs": result["sample_inputs"].tolist() if "sample_inputs" in result else [],
    }


@app.get("/api/captures/{capture_id}/shap")
def get_shap(capture_id: str):
    capture = _get_capture_or_404(capture_id)
    if not os.path.exists(capture["npz_path"]):
        return {"available": False}

    result = shap_from_arrays(_load_npz(capture["npz_path"]))
    if result is None:
        return {"available": False}

    values = result["values"]
    response = {"available": True, "values": values.tolist(), "shape": list(values.shape)}
    if "base_values" in result:
        response["base_values"] = result["base_values"].tolist()
    return response


_static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


def main():
    parser = argparse.ArgumentParser(prog="lensnn")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("runs_dir")
    serve_parser.add_argument("--port", type=int, default=config.DEFAULT_SERVER_PORT)
    serve_parser.add_argument("--host", default=config.DEFAULT_SERVER_HOST)

    args = parser.parse_args()

    if args.command == "serve":
        set_runs_dir(args.runs_dir)
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
