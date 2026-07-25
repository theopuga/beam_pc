"""Project paths. All caches/datasets live under <repo>/data/ (gitignored)."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
GUIDE_CACHE_DIR = CACHE_DIR / "guides"
# iFixit step images, downloaded by the fetcher for guide display/demo only.
# CC BY-NC-SA 3.0 — never training data. Training images live in DATASET_DIR.
GUIDE_IMAGES_DIR = DATA_DIR / "guide_images"
DATASET_DIR = DATA_DIR / "dataset"

# Device registry (committed, source of truth for labels) and the local fetch
# audit log (gitignored).
DEVICES_JSON = DATA_DIR / "devices.json"
FETCH_INDEX = DATA_DIR / "fetch_index.jsonl"

CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"


def ensure_dirs() -> None:
    for d in (GUIDE_CACHE_DIR, GUIDE_IMAGES_DIR, DATASET_DIR, CHECKPOINT_DIR):
        d.mkdir(parents=True, exist_ok=True)
