# AGENTS.md

## Project

Learning-exercise CV repo: identify a device from a photo, then retrieve repair
guides. Python 3.10+, src layout, package `beam_pc`.

## Layout

- `src/beam_pc/ifixit/` — API client, models, image download, `fetch` CLI
- `src/beam_pc/data/` — dataset manifest (JSONL), label helpers
- `src/beam_pc/vision/` — model/train/infer; **torch imports are lazy** so the
  core package stays light. Don't import torch at module top level.
- `src/beam_pc/pipeline.py` — end-to-end glue
- `data/` — gitignored caches (`cache/`, `guide_images/`, `dataset/`)
- `tests/` — pytest, no network access in tests

## Data separation (hard rule)

- `data/guide_images/` — iFixit step images, **display/demo only, never
  training data** (CC BY-NC-SA; iFixit ToS bans ML training on their content).
- `data/dataset/` — training images: own photos / permissively licensed only.
- Never wire `guide_images/` into dataset/manifest/training code.

## Commands

```powershell
pip install -e .[dev]                  # setup
pytest                                 # tests (offline)
python -m beam_pc.ifixit.fetch --query "iphone 13 battery" --limit 3
```

## Conventions

- stdlib dataclasses for API models (no pydantic)
- `requests` for HTTP; all calls go through `IFixitClient` (rate limit + cache)
- Keep it simple; skeleton code over clever code
