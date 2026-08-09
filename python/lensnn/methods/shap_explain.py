import numpy as np
import shap
import torch

from .. import config
from ..utils.model_wrapper import wrap_model

SHAP_PREFIX = "shap"


def _to_array(inputs):
    if isinstance(inputs, torch.Tensor):
        return inputs.detach().cpu().numpy()
    return np.asarray(inputs)


def _sample_background(data, n_samples):
    if len(data) <= n_samples:
        return data
    idx = np.random.choice(len(data), size=n_samples, replace=False)
    return data[idx]


def compute_shap(model, inputs, predict_fn=None, background_samples=None):
    """SHAP feature attributions for a batch of tabular inputs.

    predict_fn: explicit override; otherwise wrap_model() auto-detects a
    PyTorch nn.Module or an sklearn-like model (predict_proba/predict).
    background_samples: baseline size, drawn from `inputs` itself
    (defaults to config.SHAP_BACKGROUND_SAMPLES).
    Returns {"values": ndarray, "base_values": ndarray | None}.
    """
    predict_fn = predict_fn or wrap_model(model)
    inputs_arr = _to_array(inputs)
    n_background = background_samples or config.SHAP_BACKGROUND_SAMPLES
    background = _sample_background(inputs_arr, n_background)

    explainer = shap.Explainer(predict_fn, background)
    explanation = explainer(inputs_arr)

    values = np.asarray(explanation.values)
    base_values = getattr(explanation, "base_values", None)
    if base_values is not None:
        base_values = np.asarray(base_values)
    return {"values": values, "base_values": base_values}


def to_arrays(result):
    """Serialize a compute_shap() result into a flat, namespaced dict of
    arrays for merging into a capture .npz."""
    if result is None:
        return {}
    payload = {f"{SHAP_PREFIX}/values": result["values"]}
    if result.get("base_values") is not None:
        payload[f"{SHAP_PREFIX}/base_values"] = result["base_values"]
    return payload


def from_arrays(arrays):
    """Inverse of to_arrays(). Returns None if no SHAP data is present."""
    values_key = f"{SHAP_PREFIX}/values"
    if values_key not in arrays:
        return None
    result = {"values": arrays[values_key]}
    base_key = f"{SHAP_PREFIX}/base_values"
    if base_key in arrays:
        result["base_values"] = arrays[base_key]
    return result
