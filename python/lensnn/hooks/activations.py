import numpy as np
import torch

from .. import config

ACTIVATIONS_PREFIX = "activations"


def capture_activations(model, input_batch):
    model.eval()
    raw = {}
    handles = [
        _register_hook(name, module, raw)
        for name, module in model.named_modules()
        if name
    ]
    with torch.no_grad():
        model(input_batch)
    for handle in handles:
        handle.remove()
    return {name: _summarize(tensor) for name, tensor in raw.items()}


def _register_hook(name, module, raw):
    def hook(_module, _inputs, output):
        if isinstance(output, torch.Tensor):
            raw[name] = output.detach()

    return module.register_forward_hook(hook)


def _summarize(tensor):
    arr = tensor.cpu().numpy()
    stats = {"shape": list(arr.shape), "mean": float(arr.mean()), "std": float(arr.std())}
    if arr.size <= config.MAX_ACTIVATION_ARRAY_SIZE:
        stats["full"] = arr
    return stats


def to_arrays(activations):
    """Serialize captured activations to a flat dict of arrays, namespaced
    so they can be merged into a single capture .npz alongside other
    methods' arrays."""
    payload = {}
    for layer, stats in activations.items():
        key = f"{ACTIVATIONS_PREFIX}/{layer}"
        payload[f"{key}__mean"] = np.array(stats["mean"])
        payload[f"{key}__std"] = np.array(stats["std"])
        payload[f"{key}__shape"] = np.array(stats["shape"])
        if "full" in stats:
            payload[f"{key}__full"] = stats["full"]
    return payload


def from_arrays(arrays):
    """Inverse of to_arrays(). `arrays` is any dict-like mapping of
    key -> ndarray (e.g. a loaded .npz)."""
    prefix = f"{ACTIVATIONS_PREFIX}/"
    fields_by_layer = {}
    for key in arrays:
        if not key.startswith(prefix):
            continue
        layer, field = key[len(prefix):].rsplit("__", 1)
        fields_by_layer.setdefault(layer, {})[field] = arrays[key]

    result = {}
    for layer, fields in fields_by_layer.items():
        result[layer] = {
            "shape": fields["shape"].tolist(),
            "mean": float(fields["mean"]),
            "std": float(fields["std"]),
        }
        if "full" in fields:
            result[layer]["full"] = fields["full"].tolist()
    return result
