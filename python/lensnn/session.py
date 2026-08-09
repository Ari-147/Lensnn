import os
import uuid
from datetime import datetime, timezone

import numpy as np
import torch

from . import config
from .storage import db
from .hooks.activations import capture_activations, to_arrays as activations_to_arrays
from .methods.gradcam import compute_gradcam, has_conv_layers, to_arrays as gradcam_to_arrays


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


def _to_target_tensor(labels):
    if isinstance(labels, torch.Tensor):
        return labels
    return torch.as_tensor(np.asarray(labels))


def _summarize_model(model):
    if isinstance(model, torch.nn.Module):
        n_params = sum(p.numel() for p in model.parameters())
        return f"{model.__class__.__name__} ({n_params} params)"
    return model.__class__.__name__


def _save_npz(npz_path, payload):
    dirname = os.path.dirname(npz_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    np.savez_compressed(npz_path, **payload)


class Session:
    def __init__(self, name, runs_dir=None):
        self.name = name
        self.runs_dir = runs_dir or config.RUNS_DIR
        self.run_id = str(uuid.uuid4())
        self.framework = None
        self.db_path = db.default_db_path(self.runs_dir)
        db.init_db(self.db_path)
        db.insert_run(self.db_path, self.run_id, self.name, "unknown", _now_iso())

    def log_epoch(self, epoch, model, val_batch, val_labels):
        return self._capture(step=epoch, model=model, inputs=val_batch, labels=val_labels)

    def explain(self, model, inputs, labels=None):
        return self._capture(step=None, model=model, inputs=inputs, labels=labels)

    def _capture(self, step, model, inputs, labels=None):
        framework = _detect_framework(model)
        if self.framework is None:
            self.framework = framework
            db.update_run_framework(self.db_path, self.run_id, framework)

        npz_payload = {}
        if isinstance(model, torch.nn.Module):
            tensor_inputs = _to_tensor(inputs)
            activations = capture_activations(model, tensor_inputs)
            npz_payload.update(activations_to_arrays(activations))

            if has_conv_layers(model):
                n = min(tensor_inputs.shape[0], config.GRADCAM_MAX_SAMPLES)
                sample_inputs = tensor_inputs[:n]
                target = _to_target_tensor(labels)[:n] if labels is not None else None
                gradcam_result = compute_gradcam(model, sample_inputs, target=target)
                npz_payload.update(gradcam_to_arrays(gradcam_result, sample_inputs=sample_inputs))

        capture_id = str(uuid.uuid4())
        npz_path = os.path.join(self.runs_dir, self.run_id, f"{capture_id}.npz")
        _save_npz(npz_path, npz_payload)

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
