# beam_pc

Computer vision pipeline to help people fix phones / PCs / laptops: photograph a
device, identify it, and surface the right repair guide.

**Status:** early scaffold. Learning project.

## Architecture

```
photo → [vision model: device/part ID] → [iFixit API: guide retrieval] → step-by-step repair guidance
```

Three layers, each independently usable:

| Layer | Module | What it does |
|---|---|---|
| Retrieval | `beam_pc.ifixit` | Rate-limited client for the public iFixit API (search, guides, categories, image download with caching) |
| Data | `beam_pc.data` | Dataset layout, labels, and JSONL manifests for self-collected images |
| Vision | `beam_pc.vision` | Device classifier (fine-tuned ResNet), training loop, inference |

`beam_pc.pipeline` glues them: image in → predicted device → matching iFixit guides out.

## Quickstart

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]        # core + tests (light)
pip install -e .[vision]     # only when ready to train (pulls torch)
```

Fetch a guide via the API:

```powershell
python -m beam_pc.ifixit.fetch --query "iphone 13 battery" --limit 3
```

Run the end-to-end pipeline (once a checkpoint exists):

```powershell
python -m beam_pc.pipeline photo.jpg --checkpoint checkpoints\device_clf.pt
```

## Data strategy

The vision model trains on **self-collected / permissively licensed images only**
(own teardown photos, community submissions, synthetic renders). See
`src/beam_pc/data/manifest.py` for the dataset layout.

## Legal notes

- iFixit content is **CC BY-NC-SA 3.0**: attribution required, non-commercial use
  only, share-alike. Anything shown to users from iFixit must credit and link them.
- iFixit's Terms of Use **prohibit using their data to train ML/AI models**.
  The iFixit layer here is strictly *runtime retrieval* — guides are fetched
  per-request and cached locally, never used as training data.
- This repo is a personal learning exercise, non-commercial by design.

## Roadmap

- [x] iFixit API client with caching + rate limiting
- [x] Dataset manifest + training skeleton
- [ ] Collect initial device dataset (~20 models, own photos)
- [ ] Train v1 device classifier
- [ ] Damage/part identification
