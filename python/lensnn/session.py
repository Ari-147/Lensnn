import os
import uuid
from datetime import datetime, timezone

import numpy as np
import torch

from . import config
from .storage import db
from .hooks.activations import capture_activations, save_activations


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _detect_framework(model):
    if isinstance(model, torch.nn.Module):
        return "pytorch"
    if hasattr(model, "predict_proba") or hasattr(model, "predict"):
        return "sklearn"
    return "unknown"


def _to_tensor(inputs):
    if isinstance(inputs, torch.Tensor):
        return inputs
    return torch.as_tensor(np.asarray(inputs), dtype=torch.float32)


def _summarize_model(model):
    if isinstance(model, torch.nn.Module):
        n_params = sum(p.numel() for p in model.parameters())
        return f"{model.__class__.__name__} ({n_params} params)"
    return model.__class__.__name__


class Session:
    def __init__(self, name, runs_dir=None):
        self.name = name
        self.runs_dir = runs_dir or config.RUNS_DIR
        self.run_id = str(uuid.uuid4())
        self.framework = None
        self.db_path = db.default_db_path(self.runs_dir)
        db.init_db(self.db_path)
        db.insert_run(self.db_path, self.run_id, self.name, "unknown", _now_iso())

    def log_epoch(self, epoch, model, val_batch, val_labels=None):
        return self._capture(step=epoch, model=model, inputs=val_batch)

    def explain(self, model, inputs, labels=None):
        return self._capture(step=None, model=model, inputs=inputs)

    def _capture(self, step, model, inputs):
        framework = _detect_framework(model)
        if self.framework is None:
            self.framework = framework
            db.update_run_framework(self.db_path, self.run_id, framework)

        activations = {}
        if isinstance(model, torch.nn.Module):
            activations = capture_activations(model, _to_tensor(inputs))

        capture_id = str(uuid.uuid4())
        npz_path = os.path.join(self.runs_dir, self.run_id, f"{capture_id}.npz")
        save_activations(npz_path, activations)

        db.insert_capture(
            self.db_path,
            capture_id,
            self.run_id,
            step,
            _now_iso(),
            npz_path,
            _summarize_model(model),
        )
        return capture_id
