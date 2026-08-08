import argparse
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .. import config
from ..storage import db
from ..hooks.activations import load_activations

app = FastAPI(title="LensNN Viewer")
_state = {"runs_dir": config.RUNS_DIR}


def set_runs_dir(runs_dir):
    _state["runs_dir"] = runs_dir


def _db_path():
    return db.default_db_path(_state["runs_dir"])


@app.get("/api/runs")
def get_runs():
    return db.list_runs(_db_path())


@app.get("/api/runs/{run_id}/captures")
def get_captures(run_id: str):
    return db.list_captures(_db_path(), run_id)


@app.get("/api/captures/{capture_id}/activations")
def get_activations(capture_id: str):
    capture = db.get_capture(_db_path(), capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="capture not found")
    if not os.path.exists(capture["npz_path"]):
        return {}
    return load_activations(capture["npz_path"])


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
