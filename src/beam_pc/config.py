"""Project paths. All caches/datasets live under <repo>/data/ (gitignored)."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
GUIDE_CACHE_DIR = CACHE_DIR / "guides"
IMAGE_DIR = DATA_DIR / "images"
DATASET_DIR = DATA_DIR / "dataset"

CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"


def ensure_dirs() -> None:
    for d in (GUIDE_CACHE_DIR, IMAGE_DIR, DATASET_DIR, CHECKPOINT_DIR):
        d.mkdir(parents=True, exist_ok=True)
