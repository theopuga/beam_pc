"""Inference: photo -> (device_label, confidence)."""

from __future__ import annotations

from pathlib import Path

from beam_pc.vision.model import load_checkpoint


class DeviceClassifier:
    def __init__(self, checkpoint: str | Path):
        self.net, self.classes = load_checkpoint(Path(checkpoint))

    def predict(self, image_path: str | Path) -> tuple[str, float]:
        import torch
        from PIL import Image
        from torchvision import transforms

        tf = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        img = tf(Image.open(image_path).convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            probs = torch.softmax(self.net(img), dim=1)[0]
        idx = int(probs.argmax())
        return self.classes[idx], float(probs[idx])
