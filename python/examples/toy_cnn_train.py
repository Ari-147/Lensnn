"""Train a tiny CNN on a handful of synthetic images, logging Grad-CAM
heatmaps to LensNN each epoch plus a final explain() pass.

Run from python/:
    python examples/toy_cnn_train.py
    lensnn serve ./runs
Then open http://127.0.0.1:8000, pick the toy_cnn run, and check the
Grad-CAM panel highlights the bright patch (top-left corner) on samples
labeled class 1.
"""
import torch
import torch.nn as nn

from lensnn.session import Session

N_EPOCHS = 15
N_SAMPLES = 8
IMG_SIZE = 16
PATCH_SIZE = 4
N_CLASSES = 2
LEARNING_RATE = 0.01


def make_synthetic_images(n, size, patch_size, seed=0):
    """A handful of tiny images: class 1 has a bright patch in the
    top-left corner, class 0 is plain noise. Gives Grad-CAM something
    sensible to localize."""
    gen = torch.Generator().manual_seed(seed)
    images = torch.randn(n, 3, size, size, generator=gen) * 0.1
    labels = torch.randint(0, N_CLASSES, (n,), generator=gen)
    for i in range(n):
        if labels[i] == 1:
            images[i, :, :patch_size, :patch_size] += 2.0
    return images, labels


class TinyCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 8, kernel_size=3, padding=1)
        self.relu1 = nn.ReLU()
        self.conv2 = nn.Conv2d(8, 16, kernel_size=3, padding=1)
        self.relu2 = nn.ReLU()
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(16, N_CLASSES)

    def forward(self, x):
        x = self.relu1(self.conv1(x))
        x = self.relu2(self.conv2(x))
        x = self.pool(x).flatten(1)
        return self.fc(x)


def main():
    images, labels = make_synthetic_images(N_SAMPLES, IMG_SIZE, PATCH_SIZE)
    model = TinyCNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_fn = nn.CrossEntropyLoss()

    session = Session("toy_cnn")

    for epoch in range(N_EPOCHS):
        optimizer.zero_grad()
        loss = loss_fn(model(images), labels)
        loss.backward()
        optimizer.step()

        session.log_epoch(epoch, model, images, labels)
        print(f"epoch {epoch}: loss={loss.item():.4f} (activations + gradcam captured)")

    session.explain(model, images, labels=labels)
    print(f"\nRun saved: run_id={session.run_id} in {session.runs_dir}")
    print("View it with: lensnn serve ./runs")


if __name__ == "__main__":
    main()
