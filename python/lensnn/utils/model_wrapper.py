import numpy as np
import torch


def wrap_model(model=None, framework=None, predict_fn=None):
    """Return a unified Callable[[array], array] for any supported model."""
    if predict_fn is not None:
        return predict_fn

    if framework == "torch" or (framework is None and isinstance(model, torch.nn.Module)):
        return _wrap_torch(model)

    if framework == "sklearn" or (framework is None and _is_sklearn_like(model)):
        return _wrap_sklearn(model)

    raise ValueError(
        "wrap_model() could not auto-detect the model type. "
        "Pass predict_fn=<callable> explicitly for unsupported model types."
    )


def _is_sklearn_like(model):
    return hasattr(model, "predict_proba") or hasattr(model, "predict")


def _wrap_torch(model):
    model.eval()

    def predict(x):
        tensor = x if isinstance(x, torch.Tensor) else torch.as_tensor(np.asarray(x), dtype=torch.float32)
        with torch.no_grad():
            out = model(tensor)
        if out.dim() == 2 and out.shape[1] > 1:
            # Multi-class output: assume raw logits (the standard PyTorch
            # convention, since nn.CrossEntropyLoss expects logits) and
            # normalize to probabilities. SHAP, LIME, boundary, and
            # calibration all treat predict_fn's output as a probability
            # distribution (LIME enforces rows summing to 1; calibration's
            # confidence is meaningless otherwise). Single-output models
            # (regression, or shape [N, 1]) are left untouched.
            out = torch.softmax(out, dim=1)
        return out.detach().cpu().numpy()

    return predict


def _wrap_sklearn(model):
    if hasattr(model, "predict_proba"):
        return lambda x: model.predict_proba(np.asarray(x))
    return lambda x: model.predict(np.asarray(x))
