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
from ..methods.lime_explain import from_arrays as lime_from_arrays
from ..methods.boundary import from_arrays as boundary_from_arrays
from ..methods.calibration import from_arrays as calibration_from_arrays

app = FastAPI(title="LensNN Viewer")
_state = {"runs_dir": config.RUNS_DIR}


def set_runs_dir(runs_dir):
    _state["runs_dir"] = runs_dir


def _db_path():
    return db.default_db_path(_state["runs_dir"])


def _load_npz(npz_path):
    with np.load(npz_path, allow_pickle=False) as npz:
        return {key: npz[key] for key in npz.files}


def _npz_prefixes(npz_path):
    """Cheap check of which method namespaces a capture's .npz contains,
    without decompressing any array payloads (just the zip directory
    listing) — used to decide which tabs to show without pulling data."""
    with np.load(npz_path, allow_pickle=False) as npz:
        keys = npz.files
    return {key.split("/", 1)[0] for key in keys if "/" in key}


def _get_capture_or_404(capture_id):
    capture = db.get_capture(_db_path(), capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="capture not found")
    return capture


@app.get("/api/runs")
def get_runs():
    return db.list_runs(_db_path())


@app.get("/api/runs/{run_id}/captures")
def get_captures(run_id: str, limit: int | None = None, offset: int = 0):
    if limit is None:
        limit = config.CAPTURES_PAGE_SIZE
    captures = db.list_captures(_db_path(), run_id, limit=limit, offset=offset)
    total = db.count_captures(_db_path(), run_id)
    return {"captures": captures, "total": total, "offset": offset, "limit": limit}


@app.get("/api/captures/{capture_id}/panels")
def get_available_panels(capture_id: str):
    capture = _get_capture_or_404(capture_id)
    panel_names = ("activations", "gradcam", "shap", "lime", "boundary", "calibration")
    if not os.path.exists(capture["npz_path"]):
        return {name: False for name in panel_names}
    prefixes = _npz_prefixes(capture["npz_path"])
    return {name: name in prefixes for name in panel_names}


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


@app.get("/api/captures/{capture_id}/lime")
def get_lime(capture_id: str):
    capture = _get_capture_or_404(capture_id)
    if not os.path.exists(capture["npz_path"]):
        return {"available": False}

    result = lime_from_arrays(_load_npz(capture["npz_path"]))
    if result is None:
        return {"available": False}

    values = result["values"]
    return {"available": True, "values": values.tolist(), "shape": list(values.shape)}


@app.get("/api/captures/{capture_id}/boundary")
def get_boundary(capture_id: str):
    capture = _get_capture_or_404(capture_id)
    if not os.path.exists(capture["npz_path"]):
        return {"available": False}

    result = boundary_from_arrays(_load_npz(capture["npz_path"]))
    if result is None:
        return {"available": False}

    response = {
        "available": True,
        "grid_x": result["grid_x"].tolist(),
        "grid_y": result["grid_y"].tolist(),
        "grid_values": result["grid_values"].tolist(),
        "points_2d": result["points_2d"].tolist(),
        "point_pred_values": result["point_pred_values"].tolist(),
    }
    if "point_true_values" in result:
        response["point_true_values"] = result["point_true_values"].tolist()
    return response


@app.get("/api/captures/{capture_id}/calibration")
def get_calibration(capture_id: str):
    capture = _get_capture_or_404(capture_id)
    if not os.path.exists(capture["npz_path"]):
        return {"available": False}

    result = calibration_from_arrays(_load_npz(capture["npz_path"]))
    if result is None:
        return {"available": False}

    return {
        "available": True,
        "bin_edges": result["bin_edges"].tolist(),
        "bin_confidence": result["bin_confidence"].tolist(),
        "bin_accuracy": result["bin_accuracy"].tolist(),
        "bin_count": result["bin_count"].tolist(),
        "ece": result["ece"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


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
