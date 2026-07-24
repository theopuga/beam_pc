"""Dataset manifest: a JSONL index over self-collected training images.

Layout on disk (gitignored):

    data/dataset/
        <device_label>/          # e.g. "iphone_13", "thinkpad_t480"
            img001.jpg
            ...
        manifest.jsonl           # one DatasetEntry per line

Only self-collected or permissively licensed images go here. Never iFixit
content (their ToS bans ML training on their data).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

VALID_SOURCES = {"own_photo", "community", "synthetic", "permissive_license"}


@dataclass
class DatasetEntry:
    image_path: str          # relative to dataset dir
    device_label: str        # e.g. "iphone_13"
    source: str              # one of VALID_SOURCES
    part_label: str = ""     # optional finer label, e.g. "battery_connector"
    split: str = "train"     # train | val | test


def write_manifest(entries: list[DatasetEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for e in entries:
            if e.source not in VALID_SOURCES:
                raise ValueError(f"invalid source {e.source!r} for {e.image_path}")
            f.write(json.dumps(asdict(e)) + "\n")


def load_manifest(path: Path) -> list[DatasetEntry]:
    return [DatasetEntry(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def scan_dataset_dir(dataset_dir: Path, source: str = "own_photo") -> list[DatasetEntry]:
    """Build entries from the folder layout: data/dataset/<device_label>/*.jpg"""
    entries: list[DatasetEntry] = []
    for class_dir in sorted(p for p in dataset_dir.iterdir() if p.is_dir()):
        for img in sorted(class_dir.glob("*")):
            if img.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                entries.append(
                    DatasetEntry(
                        image_path=str(img.relative_to(dataset_dir)),
                        device_label=class_dir.name,
                        source=source,
                    )
                )
    return entries
