import numpy as np
import torch
from captum.attr import LayerAttribution, LayerGradCam

GRADCAM_PREFIX = "gradcam"


def has_conv_layers(model):
    return any(isinstance(m, torch.nn.Conv2d) for m in model.modules())


def find_last_conv_layer(model):
    """Return (name, module) of the last nn.Conv2d in registration order,
    or (None, None) if the model has no conv layers."""
    last = None
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.Conv2d):
            last = (name, module)
    return last if last is not None else (None, None)


def compute_gradcam(model, inputs, target=None, layer=None, layer_name=None):
    """Grad-CAM heatmaps for a batch of image inputs [N, C, H, W].

    layer: explicit nn.Module to target; overrides auto-detection.
    target: per-sample class index tensor; defaults to the model's own
    predicted class per sample.
    Returns {"layer_name": str, "heatmaps": ndarray [N, H, W] in [0, 1]},
    or None if the model has no conv layer to target.
    """
    model.eval()
    if layer is None:
        layer_name, layer = find_last_conv_layer(model)
        if layer is None:
            return None
    elif layer_name is None:
        layer_name = "custom"

    if target is None:
        with torch.no_grad():
            target = model(inputs).argmax(dim=1)

    gradcam = LayerGradCam(model, layer)
    attributions = gradcam.attribute(inputs, target=target, relu_attributions=True)
    upsampled = LayerAttribution.interpolate(attributions, inputs.shape[-2:])
    heatmaps = _normalize(upsampled.squeeze(1).detach().cpu().numpy())
    return {"layer_name": layer_name, "heatmaps": heatmaps}


def _normalize(heatmaps):
    out = np.empty_like(heatmaps)
    for i in range(heatmaps.shape[0]):
        h = heatmaps[i]
        lo, hi = float(h.min()), float(h.max())
        out[i] = (h - lo) / (hi - lo) if hi > lo else np.zeros_like(h)
    return out


def to_arrays(result, sample_inputs=None):
    """Serialize a compute_gradcam() result (plus the sample inputs it was
    computed on, so the viewer can overlay heatmaps on the original image)
    into a flat, namespaced dict of arrays."""
    if result is None:
        return {}
    payload = {
        f"{GRADCAM_PREFIX}/layer_name": np.array(result["layer_name"]),
        f"{GRADCAM_PREFIX}/heatmaps": result["heatmaps"],
    }
    if sample_inputs is not None:
        arr = sample_inputs.detach().cpu().numpy() if isinstance(sample_inputs, torch.Tensor) else np.asarray(sample_inputs)
        payload[f"{GRADCAM_PREFIX}/sample_inputs"] = arr
    return payload


def from_arrays(arrays):
    """Inverse of to_arrays(). `arrays` is any dict-like mapping of
    key -> ndarray (e.g. a loaded .npz). Returns None if no Grad-CAM data
    is present (e.g. the model had no conv layers)."""
    heatmap_key = f"{GRADCAM_PREFIX}/heatmaps"
    if heatmap_key not in arrays:
        return None
    result = {
        "layer_name": arrays[f"{GRADCAM_PREFIX}/layer_name"].item(),
        "heatmaps": arrays[heatmap_key],
    }
    sample_key = f"{GRADCAM_PREFIX}/sample_inputs"
    if sample_key in arrays:
        result["sample_inputs"] = arrays[sample_key]
    return result
