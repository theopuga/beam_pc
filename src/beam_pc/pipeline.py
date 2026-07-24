"""End-to-end: photo -> device ID -> matching iFixit repair guides.

    python -m beam_pc.pipeline photo.jpg --checkpoint checkpoints/device_clf.pt --repair battery
"""

from __future__ import annotations

import argparse
from pathlib import Path

from beam_pc.ifixit.client import IFixitClient
from beam_pc.ifixit.models import ATTRIBUTION, GuideSummary


def guides_for_photo(
    image_path: str | Path,
    checkpoint: str | Path,
    repair: str = "",
    limit: int = 5,
) -> tuple[str, float, list[GuideSummary]]:
    from beam_pc.vision.infer import DeviceClassifier  # lazy: needs torch

    clf = DeviceClassifier(checkpoint)
    label, confidence = clf.predict(image_path)

    query = f"{label.replace('_', ' ')} {repair}".strip()
    results = IFixitClient().search_guides(query, limit=limit)
    return label, confidence, results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="photo of the device")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--repair", default="", help="e.g. battery, screen")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    label, conf, results = guides_for_photo(args.image, args.checkpoint, args.repair, args.limit)
    print(f"Identified: {label} ({conf:.0%} confident)\n")
    for r in results:
        print(f"[{r.guideid}] {r.title}  ({r.difficulty or 'n/a'})")
        print(f"    {r.url}")
    print(f"\n{ATTRIBUTION}")


if __name__ == "__main__":
    main()
