"""Train a tiny PyTorch model, logging activations to LensNN each epoch,
then run a final explain() pass (SHAP + LIME + activations) on a held-out
batch.

Run from python/:
    python examples/toy_train.py
    lensnn serve ./runs
Then open http://127.0.0.1:8000 and pick the run to see per-epoch
activation stats, plus the SHAP and LIME panels on the final "explain"
capture.
"""
import torch
import torch.nn as nn

from lensnn.session import Session

N_EPOCHS = 5
BATCH_SIZE = 16
IN_FEATURES = 10
N_CLASSES = 2


def main():
    model = nn.Sequential(
        nn.Linear(IN_FEATURES, 32),
        nn.ReLU(),
        nn.Linear(32, N_CLASSES),
    )
    optimizer = torch.optim.Adam(model.parameters())
    loss_fn = nn.CrossEntropyLoss()

    session = Session("toy_train")

    for epoch in range(N_EPOCHS):
        train_batch = torch.randn(BATCH_SIZE, IN_FEATURES)
        train_labels = torch.randint(0, N_CLASSES, (BATCH_SIZE,))

        optimizer.zero_grad()
        loss = loss_fn(model(train_batch), train_labels)
        loss.backward()
        optimizer.step()

        val_batch = torch.randn(BATCH_SIZE, IN_FEATURES)
        val_labels = torch.randint(0, N_CLASSES, (BATCH_SIZE,))
        session.log_epoch(epoch, model, val_batch, val_labels)

        print(f"epoch {epoch}: loss={loss.item():.4f} (activations captured)")

    holdout_batch = torch.randn(BATCH_SIZE, IN_FEATURES)
    holdout_labels = torch.randint(0, N_CLASSES, (BATCH_SIZE,))
    session.explain(model, holdout_batch, labels=holdout_labels)

    print(f"\nRun saved: run_id={session.run_id} in {session.runs_dir}")
    print("View it with: lensnn serve ./runs")


if __name__ == "__main__":
    main()
