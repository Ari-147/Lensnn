import numpy as np
import torch

from .. import config
from ..utils.model_wrapper import wrap_model

CALIBRATION_PREFIX = "calibration"


def _to_array(inputs):
    if isinstance(inputs, torch.Tensor):
        return inputs.detach().cpu().numpy()
    return np.asarray(inputs)


def compute_calibration(model, inputs, labels, predict_fn=None, num_bins=None):
    """Reliability diagram data + Expected Calibration Error over a
    dataset. Requires true labels (there's no accuracy to measure
    without them); returns None if labels is None.

    predict_fn: explicit override; otherwise wrap_model() auto-detects a
    PyTorch nn.Module or an sklearn-like model. Assumes predict_fn
    returns probabilities (as sklearn's predict_proba does); confidence
    is clipped to [0, 1] as a defensive measure against raw logits.
    """
    if labels is None:
        return None

    predict_fn = predict_fn or wrap_model(model)
    inputs_arr = _to_array(inputs)
    labels_arr = _to_array(labels).astype(int)

    preds = np.asarray(predict_fn(inputs_arr))
    if preds.ndim == 2 and preds.shape[1] > 1:
        confidences = preds.max(axis=1)
        predicted_classes = preds.argmax(axis=1)
    else:
        confidences = preds.reshape(-1)
        predicted_classes = (confidences >= 0.5).astype(int)
    confidences = np.clip(confidences, 0.0, 1.0)

    correct = (predicted_classes == labels_arr).astype(float)

    n_bins = num_bins or config.CALIBRATION_BINS
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.clip(np.digitize(confidences, bin_edges[1:-1], right=True), 0, n_bins - 1)

    bin_confidence = np.zeros(n_bins)
    bin_accuracy = np.zeros(n_bins)
    bin_count = np.zeros(n_bins)
    for b in range(n_bins):
        mask = bin_indices == b
        count = int(mask.sum())
        bin_count[b] = count
        if count > 0:
            bin_confidence[b] = confidences[mask].mean()
            bin_accuracy[b] = correct[mask].mean()

    n = len(confidences)
    ece = float(np.sum(bin_count / n * np.abs(bin_accuracy - bin_confidence)))

    return {
        "bin_edges": bin_edges,
        "bin_confidence": bin_confidence,
        "bin_accuracy": bin_accuracy,
        "bin_count": bin_count,
        "ece": ece,
    }


def to_arrays(result):
    """Serialize a compute_calibration() result into a flat, namespaced
    dict of arrays for merging into a capture .npz."""
    if result is None:
        return {}
    return {
        f"{CALIBRATION_PREFIX}/bin_edges": result["bin_edges"],
        f"{CALIBRATION_PREFIX}/bin_confidence": result["bin_confidence"],
        f"{CALIBRATION_PREFIX}/bin_accuracy": result["bin_accuracy"],
        f"{CALIBRATION_PREFIX}/bin_count": result["bin_count"],
        f"{CALIBRATION_PREFIX}/ece": np.array(result["ece"]),
    }


def from_arrays(arrays):
    """Inverse of to_arrays(). Returns None if no calibration data is
    present (e.g. no labels were given to explain())."""
    key = f"{CALIBRATION_PREFIX}/ece"
    if key not in arrays:
        return None
    return {
        "bin_edges": arrays[f"{CALIBRATION_PREFIX}/bin_edges"],
        "bin_confidence": arrays[f"{CALIBRATION_PREFIX}/bin_confidence"],
        "bin_accuracy": arrays[f"{CALIBRATION_PREFIX}/bin_accuracy"],
        "bin_count": arrays[f"{CALIBRATION_PREFIX}/bin_count"],
        "ece": float(arrays[key]),
    }
