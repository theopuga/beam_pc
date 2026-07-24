"""Device classifier: fine-tuned ResNet-18 head over N device classes."""


def build_classifier(num_classes: int, pretrained: bool = True):
    import torch.nn as nn
    from torchvision import models

    weights = models.ResNet18_Weights.DEFAULT if pretrained else None
    net = models.resnet18(weights=weights)
    net.fc = nn.Linear(net.fc.in_features, num_classes)
    return net


def save_checkpoint(net, class_names: list[str], path) -> None:
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": net.state_dict(), "classes": class_names}, path)


def load_checkpoint(path):
    import torch

    blob = torch.load(path, map_location="cpu", weights_only=False)
    net = build_classifier(num_classes=len(blob["classes"]), pretrained=False)
    net.load_state_dict(blob["state_dict"])
    net.eval()
    return net, blob["classes"]
