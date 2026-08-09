"""Explain a small scikit-learn classifier on a toy tabular dataset with
LensNN's session.explain(), demonstrating the sklearn-model path through
SHAP, LIME, decision boundary, and calibration (no PyTorch involved at
all).

Run from python/:
    python examples/toy_sklearn_shap.py
    lensnn serve ./runs
Then open http://127.0.0.1:8000, pick the toy_sklearn_shap run's single
"explain" capture. Compare the SHAP and LIME panels for the same sample
(both show a per-sample feature-weight bar chart with a class selector,
and should broadly agree on which features matter most). Check the
Decision Boundary panel's PCA-projected class regions with the approx.
caveat, and the Calibration panel's reliability diagram + ECE.
"""
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier

from lensnn.session import Session

N_EXPLAIN_SAMPLES = 12


def main():
    data = load_iris()
    model = RandomForestClassifier(n_estimators=50, random_state=0)
    model.fit(data.data, data.target)

    sample_inputs = data.data[:N_EXPLAIN_SAMPLES]
    sample_labels = data.target[:N_EXPLAIN_SAMPLES]

    session = Session("toy_sklearn_shap")
    session.explain(model, sample_inputs, labels=sample_labels)

    print(f"Run saved: run_id={session.run_id} in {session.runs_dir}")
    print("View it with: lensnn serve ./runs")


if __name__ == "__main__":
    main()
