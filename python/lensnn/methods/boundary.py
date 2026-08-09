import numpy as np
import torch
from sklearn.decomposition import PCA

from .. import config
from ..utils.model_wrapper import wrap_model

BOUNDARY_PREFIX = "boundary"


def _to_array(inputs):
    if isinstance(inputs, torch.Tensor):
        return inputs.detach().cpu().numpy()
    return np.asarray(inputs)


def compute_boundary(model, inputs, predict_fn=None, labels=None):
    """PCA-projected decision boundary over a dataset.

    Fits PCA (config.PCA_COMPONENTS) on `inputs`, builds a
    config.GRID_RESOLUTION x GRID_RESOLUTION grid over that 2D space,
    inverse-transforms grid points back to the original feature space,
    and evaluates predict_fn on them. This is an approximation of the
    true decision boundary, not ground truth (the model's real boundary
    lives in the original, higher-dimensional feature space).

    predict_fn: explicit override; otherwise wrap_model() auto-detects a
    PyTorch nn.Module or an sklearn-like model.
    labels: optional true labels for the plotted points (not required
    for the boundary grid itself).
    """
    predict_fn = predict_fn or wrap_model(model)
    inputs_arr = _to_array(inputs)

    pca = PCA(n_components=config.PCA_COMPONENTS)
    points_2d = pca.fit_transform(inputs_arr)

    x_min, x_max = points_2d[:, 0].min(), points_2d[:, 0].max()
    y_min, y_max = points_2d[:, 1].min(), points_2d[:, 1].max()
    x_pad = (x_max - x_min) * 0.1 or 1.0
    y_pad = (y_max - y_min) * 0.1 or 1.0

    grid_x = np.linspace(x_min - x_pad, x_max + x_pad, config.GRID_RESOLUTION)
    grid_y = np.linspace(y_min - y_pad, y_max + y_pad, config.GRID_RESOLUTION)
    xx, yy = np.meshgrid(grid_x, grid_y)
    grid_points_2d = np.stack([xx.ravel(), yy.ravel()], axis=1)

    grid_points_original = pca.inverse_transform(grid_points_2d)
    grid_preds = np.asarray(predict_fn(grid_points_original))
    is_classification = grid_preds.ndim == 2 and grid_preds.shape[1] > 1
    grid_values = grid_preds.argmax(axis=1) if is_classification else grid_preds.reshape(-1)
    grid_values = grid_values.reshape(xx.shape)

    point_preds = np.asarray(predict_fn(inputs_arr))
    point_pred_values = point_preds.argmax(axis=1) if is_classification else point_preds.reshape(-1)

    result = {
        "grid_x": grid_x,
        "grid_y": grid_y,
        "grid_values": grid_values,
        "points_2d": points_2d,
        "point_pred_values": point_pred_values,
    }
    if labels is not None:
        result["point_true_values"] = _to_array(labels)
    return result


def to_arrays(result):
    """Serialize a compute_boundary() result into a flat, namespaced dict
    of arrays for merging into a capture .npz."""
    if result is None:
        return {}
    payload = {
        f"{BOUNDARY_PREFIX}/grid_x": result["grid_x"],
        f"{BOUNDARY_PREFIX}/grid_y": result["grid_y"],
        f"{BOUNDARY_PREFIX}/grid_values": result["grid_values"],
        f"{BOUNDARY_PREFIX}/points_2d": result["points_2d"],
        f"{BOUNDARY_PREFIX}/point_pred_values": result["point_pred_values"],
    }
    if result.get("point_true_values") is not None:
        payload[f"{BOUNDARY_PREFIX}/point_true_values"] = result["point_true_values"]
    return payload


def from_arrays(arrays):
    """Inverse of to_arrays(). Returns None if no boundary data is
    present (e.g. this was a log_epoch capture, not explain())."""
    key = f"{BOUNDARY_PREFIX}/grid_values"
    if key not in arrays:
        return None
    result = {
        "grid_x": arrays[f"{BOUNDARY_PREFIX}/grid_x"],
        "grid_y": arrays[f"{BOUNDARY_PREFIX}/grid_y"],
        "grid_values": arrays[key],
        "points_2d": arrays[f"{BOUNDARY_PREFIX}/points_2d"],
        "point_pred_values": arrays[f"{BOUNDARY_PREFIX}/point_pred_values"],
    }
    true_key = f"{BOUNDARY_PREFIX}/point_true_values"
    if true_key in arrays:
        result["point_true_values"] = arrays[true_key]
    return result
