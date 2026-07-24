"""Train the device classifier over data/dataset/<device_label>/*.jpg

    python -m beam_pc.vision.train --epochs 10
"""

from __future__ import annotations

import argparse

from beam_pc.config import CHECKPOINT_DIR, DATASET_DIR, ensure_dirs


def train(dataset_dir, epochs: int = 10, batch_size: int = 16, lr: float = 1e-3):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, random_split
    from torchvision import datasets, transforms

    from beam_pc.vision.model import build_classifier, save_checkpoint

    tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    ds = datasets.ImageFolder(dataset_dir, transform=tf)
    if len(ds) == 0:
        raise SystemExit(f"No images under {dataset_dir}. Add <device_label>/*.jpg folders first.")

    n_val = max(1, int(0.2 * len(ds)))
    train_ds, val_ds = random_split(ds, [len(ds) - n_val, n_val])
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_dl = DataLoader(val_ds, batch_size=batch_size)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = build_classifier(num_classes=len(ds.classes)).to(device)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()

    for epoch in range(epochs):
        net.train()
        total_loss = 0.0
        for x, y in train_dl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = loss_fn(net(x), y)
            loss.backward()
            opt.step()
            total_loss += loss.item()

        net.eval()
        correct = 0
        with torch.no_grad():
            for x, y in val_dl:
                correct += (net(x.to(device)).argmax(1) == y.to(device)).sum().item()
        print(f"epoch {epoch + 1}/{epochs}  loss={total_loss:.3f}  val_acc={correct / n_val:.3f}")

    out = CHECKPOINT_DIR / "device_clf.pt"
    save_checkpoint(net, list(ds.classes), out)
    print(f"saved -> {out}")
    return out


def main() -> None:
    ensure_dirs()
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--dataset-dir", default=str(DATASET_DIR))
    args = parser.parse_args()
    train(args.dataset_dir, epochs=args.epochs)


if __name__ == "__main__":
    main()
