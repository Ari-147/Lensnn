import unittest

import numpy as np
import torch
import torch.nn as nn

from lensnn.utils.model_wrapper import wrap_model


class SimpleLogitModel(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features)

    def forward(self, x):
        return self.linear(x)


class TestModelWrapper(unittest.TestCase):
    def test_wrap_torch_returns_probabilities_for_multiclass(self):
        model = SimpleLogitModel(3, 4)
        model.eval()
        predict_fn = wrap_model(model)

        inputs = np.array([[0.1, 0.2, 0.3], [0.3, 0.4, 0.5]], dtype=np.float32)
        probs = predict_fn(inputs)

        self.assertEqual(probs.shape, (2, 4))
        self.assertTrue(np.allclose(probs.sum(axis=1), np.ones(2), atol=1e-5))
        self.assertTrue(np.all(probs >= 0.0) and np.all(probs <= 1.0))

    def test_wrap_torch_preserves_regression_outputs(self):
        model = SimpleLogitModel(3, 1)
        model.eval()
        predict_fn = wrap_model(model)

        inputs = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)
        outputs = predict_fn(inputs)

        self.assertEqual(outputs.shape, (1, 1))

    def test_wrap_torch_accepts_tensor_input(self):
        model = SimpleLogitModel(3, 4)
        model.eval()
        predict_fn = wrap_model(model)

        inputs = torch.tensor([[0.1, 0.2, 0.3]], dtype=torch.float32)
        probs = predict_fn(inputs)

        self.assertEqual(probs.shape, (1, 4))
        self.assertTrue(np.allclose(probs.sum(axis=1), np.ones(1), atol=1e-5))


if __name__ == "__main__":
    unittest.main()
