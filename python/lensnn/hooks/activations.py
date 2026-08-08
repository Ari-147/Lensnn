import os

import numpy as np
import torch

from .. import config


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


def save_activations(npz_path, activations):
    dirname = os.path.dirname(npz_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    payload = {}
    for layer, stats in activations.items():
        payload[f"{layer}__mean"] = np.array(stats["mean"])
        payload[f"{layer}__std"] = np.array(stats["std"])
        payload[f"{layer}__shape"] = np.array(stats["shape"])
        if "full" in stats:
            payload[f"{layer}__full"] = stats["full"]
    np.savez_compressed(npz_path, **payload)


def load_activations(npz_path):
    data = np.load(npz_path, allow_pickle=False)
    fields_by_layer = {}
    for key in data.files:
        layer, field = key.rsplit("__", 1)
        fields_by_layer.setdefault(layer, {})[field] = data[key]

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
