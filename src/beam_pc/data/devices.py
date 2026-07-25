"""Device registry: canonical labels aligned to iFixit naming.

data/devices.json is the single source of truth tying together:

    dataset folder names (data/dataset/<label>/)
        = model class names (checkpoint classes)
        = bulk-fetch targets (ifixit_category + repair_type search queries)

Labels are lowercase snake_case derived from the iFixit category name so the
pipeline never has to guess one from the other.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_LABEL_RE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")


@dataclass
class Device:
    label: str                  # folder/class name, e.g. "iphone_13"
    ifixit_category: str        # iFixit naming, e.g. "iPhone 13"
    repair_types: list[str]     # e.g. ["battery", "screen", ...]
    aliases: list[str] = field(default_factory=list)
    min_photos: int = 30        # training-data target for this class


def label_for(category: str) -> str:
    """'Samsung Galaxy S23' -> 'samsung_galaxy_s23'."""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", category.lower())).strip("_")


def load_devices(path: Path) -> list[Device]:
    devices = [Device(**d) for d in json.loads(path.read_text(encoding="utf-8"))]
    seen: set[str] = set()
    for d in devices:
        if not _LABEL_RE.fullmatch(d.label):
            raise ValueError(f"bad label {d.label!r}: expected lowercase snake_case")
        if d.label in seen:
            raise ValueError(f"duplicate label {d.label!r}")
        seen.add(d.label)
        if not d.ifixit_category:
            raise ValueError(f"{d.label}: ifixit_category must be non-empty")
        if not d.repair_types:
            raise ValueError(f"{d.label}: repair_types must be non-empty")
    return devices
