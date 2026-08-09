import numpy as np
import torch
from lime.lime_tabular import LimeTabularExplainer

from .. import config
from ..utils.model_wrapper import wrap_model

LIME_PREFIX = "lime"


def _to_array(inputs):
    if isinstance(inputs, torch.Tensor):
        return inputs.detach().cpu().numpy()
    return np.asarray(inputs)


def _sample_background(data, n_samples):
    if len(data) <= n_samples:
        return data
    idx = np.random.choice(len(data), size=n_samples, replace=False)
    return data[idx]


def compute_lime(model, inputs, predict_fn=None, background_samples=None, num_features=None, num_samples=None):
    """LIME local feature-weight explanations for a batch of tabular
    inputs, one call to explain_instance() per sample (LIME's tabular
    explainer has no native batch API).

    predict_fn: explicit override; otherwise wrap_model() auto-detects a
    PyTorch nn.Module or an sklearn-like model (predict_proba/predict).
    Returns {"values": ndarray [N, F] for regression, or [N, F, C] for
    classification, dense with 0 for features LIME didn't select}.
    """
    predict_fn = predict_fn or wrap_model(model)
    inputs_arr = _to_array(inputs)
    n_features = inputs_arr.shape[1]

    n_background = background_samples or config.LIME_BACKGROUND_SAMPLES
    background = _sample_background(inputs_arr, n_background)
    top_k = num_features or config.LIME_NUM_FEATURES
    n_perturb = num_samples or config.LIME_NUM_SAMPLES

    probe = np.asarray(predict_fn(inputs_arr[:1]))
    is_classification = probe.ndim == 2 and probe.shape[1] > 1
    mode = "classification" if is_classification else "regression"
    n_classes = probe.shape[1] if is_classification else 1
    labels = list(range(n_classes)) if is_classification else (1,)

    explainer = LimeTabularExplainer(
        background,
        mode=mode,
        feature_names=[f"f{i}" for i in range(n_features)],
        discretize_continuous=False,
    )

    n_samples_to_explain = inputs_arr.shape[0]
    shape = (n_samples_to_explain, n_features, n_classes) if is_classification else (n_samples_to_explain, n_features)
    values = np.zeros(shape)

    for i in range(n_samples_to_explain):
        explanation = explainer.explain_instance(
            inputs_arr[i],
            predict_fn,
            num_features=min(top_k, n_features),
            num_samples=n_perturb,
            labels=labels,
        )
        if is_classification:
            for class_idx in labels:
                for feat_idx, weight in explanation.local_exp.get(class_idx, []):
                    values[i, feat_idx, class_idx] = weight
        else:
            for feat_idx, weight in explanation.local_exp.get(1, []):
                values[i, feat_idx] = weight

    return {"values": values}


def to_arrays(result):
    """Serialize a compute_lime() result into a flat, namespaced dict of
    arrays for merging into a capture .npz."""
    if result is None:
        return {}
    return {f"{LIME_PREFIX}/values": result["values"]}


def from_arrays(arrays):
    """Inverse of to_arrays(). Returns None if no LIME data is present."""
    key = f"{LIME_PREFIX}/values"
    if key not in arrays:
        return None
    return {"values": arrays[key]}
