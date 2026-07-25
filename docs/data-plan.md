# Data plan: fetching & organization

Goal: get from "empty `data/dataset/` + one cached guide" to enough data to train
the v1 device classifier and demo the end-to-end pipeline.

Two hard constraints (already encoded in the codebase):

- **iFixit images must never enter the training set** (CC BY-NC-SA + their ToS
  bans ML training). They are lookup/display content only: shown alongside
  retrieved guides in the UI/demo, nothing else.
- Tests stay offline; all network happens through `IFixitClient`.

The two image stores are deliberately separate and named to make mix-ups hard:

| Directory | Content | Used for training? |
|---|---|---|
| `data/guide_images/<guideid>/` | iFixit step images (CC BY-NC-SA) | **NO — display/demo only** |
| `data/dataset/<device_label>/` | Self-collected / permissively licensed photos | YES — the only training source |

---

## 1. What data we actually need

| # | Data | Purpose | Source | Status |
|---|------|---------|--------|--------|
| A | Training images (~20 device models, 30–50 photos each) | Train `vision.train` classifier | Own photos / permissively licensed | **missing — the blocker** |
| B | Guide corpus: cached guide JSON per device × repair type | Retrieval side of the pipeline; offline demos | iFixit API via `IFixitClient` | **fetcher proven working** — guide JSON + step images verified on disk (guide 139942, 17 images); needs bulk mode for corpus scale |
| C | Device taxonomy (label registry) | Align dataset folder names ↔ model classes ↔ iFixit category names | Manual shortlist verified via live searches | **done — 51 devices in `devices.json`** |

C comes first: without it, A gets inconsistent folder names and B can't be
fetched systematically.

---

## 2. Review: how fetch organizes data today

```
data/
  cache/guides/<guideid>.json        # raw guide payloads, keyed by id        ✅ good
  guide_images/<guideid>/000.jpg     # iFixit step images, DISPLAY-ONLY      ✅ proven, renamed for clarity
  dataset/<device_label>/*.jpg       # training images (own photos ONLY)     ✅ good split, empty
  dataset/manifest.jsonl             # index over dataset/                   ⚠️ code exists, file missing
```

What works:

- **License separation is correct and now unambiguous**: `guide_images/`
  (iFixit, view-only — the fetcher downloads these so guide steps can be
  displayed; they are never training input) vs `dataset/` (own photos, the
  only training source). Keep this wall; add an automated check (§4, phase 3).
- Guide JSON cache is simple and effective; `fetch --guide-id` is idempotent.
- Image download is proven: `fetch --guide-id 139942 --with-images` produced
  17 step images with correct extensions and cache-skip on re-run.
- Rate limiting + defensive parsing already in place.

Gaps found (status after the bulk-fetch work):

1. ~~**No canonical device labels.**~~ **RESOLVED** — `devices.json` registry:
   `label` = folder name = model class = snake_case of `ifixit_category`.
   (`pipeline.py` still guesses from the label — fixed by §5.6, one line.)
2. ~~**`categories()` / `category_devices()` are unused.**~~ **RESOLVED
   differently** — devices are verified via one real search each, which is
   stronger (it proves the fetch query, not just the category page).
3. ~~**Search results are not cached.**~~ **RESOLVED** — `cache/searches/`,
   keyed by query+limit+offset.
4. ~~**No fetch index.**~~ **RESOLVED** — `fetch_index.jsonl`, one line per
   guide with device/repair/timestamp/image count.
5. **Image naming loses step association.** `000.jpg` is the i-th image in the
   flattened guide, not step N image M. Fine for step-by-step display;
   acceptable for now, but note it in the index (store `guideid -> step order
   -> file` later only if the UI needs it). *Decision: leave naming as-is for
   v1.* (Resolved separately: the directory is now `guide_images/` so it can't
   be mistaken for a training store.)
6. ~~**`fetch` CLI fetches only `results[0]`.**~~ **RESOLVED** — bulk mode
   (`--all-devices` / `--device` / `--repair`).
7. **No split assignment.** `scan_dataset_dir` defaults everything to `train`;
   `manifest.jsonl` has never been generated.

---

## 3. Proposed layout (minimal changes)

```
data/
  cache/
    guides/<guideid>.json            # keep as-is
    searches/<query-slug>.json       # DONE: cached search results (raw result dicts)
  guide_images/<guideid>/NNN.jpg     # keep as-is (iFixit content, display-only, never training)
  dataset/<device_label>/*.jpg       # keep as-is (own photos only)
  dataset/manifest.jsonl             # generated, not hand-edited
  devices.json                       # DONE: label registry, COMMITTED to git
  fetch_index.jsonl                  # DONE: one line per fetched guide, GITIGNORED (local audit log)
```

*Decision change:* the proposed `cache/categories/` store was dropped. Device
verification uses one real search per device (`<ifixit_category> <first
repair>`), which proves the exact query the bulk fetch will use — stronger
than checking the category wiki exists, and it warms the search cache.

**`devices.json`** (lives in `data/`, committed to git — it is small,
hand-editable, and makes runs reproducible). Schema:

```json
[
  {
    "label": "iphone_13",
    "ifixit_category": "iPhone 13",
    "aliases": ["iphone 13"],
    "repair_types": ["battery", "screen"],
    "min_photos": 30
  }
]
```

Rules: `label` = folder name = model class name = lowercase/underscored form of
`ifixit_category`. The pipeline then searches `ifixit_category + repair`
instead of guessing from the label.

**`fetch_index.jsonl`** — one JSON object per line:

```json
{"guideid": 145896, "title": "...", "device_label": "iphone_13", "ifixit_category": "iPhone 13", "repair_type": "battery", "fetched_at": "2026-07-24T10:00:00Z", "with_images": true}
```

---

## 4. Fetch plan, in phases

### Phase 0 — Device shortlist ✅ DONE (broad-corpus variant)
- Decision: corpus is broad (~50 devices), not tied to what we can photograph.
  52 candidates seeded across phones/tablets/laptops/consoles/wearables.
- Verification: one live search per candidate (`<ifixit_category> <first
  repair>`); 2 had zero hits and were dropped (Galaxy Tab S6, GoPro Hero 8).
- Output: committed `devices.json` with **51 verified devices**, each with a
  per-class repair-type list (battery/screen/... for phones; fan/hdmi/... for
  consoles).

### Phase 1 — Training photos (the slow, manual part)
- 30–50 photos per device: front/back/edges, varied lighting and backgrounds,
  a few with cases on/off. Phone camera is fine; no augmentation heroics yet.
- Drop into `data/dataset/<label>/` (any filename).
- Regenerate the manifest: extend `scan_dataset_dir` (or a small CLI) to assign
  splits deterministically (e.g. every 5th image per class → `val`), then
  `write_manifest`.
- Output: `data/dataset/` populated + `manifest.jsonl` with train/val splits.

### Phase 2 — Guide corpus (bulk mode IMPLEMENTED, ready to run)
- CLI:
  `python -m beam_pc.ifixit.fetch --all-devices --with-images --limit 5`
  (`--device <label>` / `--repair <type>` to scope; dry-run proven on
  iphone_13/battery: index entry written, re-run fully cached, 0 new entries.)
- For each (device, repair_type): search (cached), fetch top-N full guides
  (cached), download step images (skip-if-present), append to
  `fetch_index.jsonl` (deduped on guideid × device × repair).
- Budget, calibrated from the dry run (iPhone battery guide = 84 images /
  74 MB; earlier guide = 17 images / 22 MB — avg ≈ 50–100 MB per device×repair
  at limit 5):
  - 51 devices × ~4.6 repair types ≈ 235 queries (searches mostly pre-cached
    by Phase 0 verification)
  - `--limit 5`: ≈ 1,000–1,200 guides → **~35–60 GB, ~4–6 h** at polite limits
    (1 s/API call, 0.5 s/image)
  - `--limit 3`: ≈ 600–700 guides → **~20–35 GB, ~2.5–4 h**
  - Disk checked: 288 GB free. Fully resumable — Ctrl+C and re-run anytime;
    caches and the index make re-runs free.
- Output: populated `cache/guides/` + `guide_images/`, `fetch_index.jsonl`
  with full coverage.

### Phase 3 — Validation
- Coverage report (script or CLI flag): photos per class vs `min_photos`,
  cached guides per device × repair type. Fail loudly on gaps.
- License guard: assert no file under `data/guide_images/` is referenced by
  `manifest.jsonl` (cheap path-prefix check; add as a test).
- `pytest` still green, still offline.

---

## 5. Code changes needed (small, in order)

1. ✅ `beam_pc/data/devices.py` — load/validate `devices.json` (+ test).
2. ✅ `client.search_guides` — on-disk cache in `cache/searches/`, keyed by
   query+limit+offset slug (+ test with StubSession).
3. ✅ `fetch.py` — bulk mode (`--device`/`--repair`/`--all-devices`) writing to
   `fetch_index.jsonl`; `--query`/`--guide-id` behavior untouched.
4. `manifest.py` — deterministic split assignment in `scan_dataset_dir` (or a
   `--val-every N` flag on a tiny CLI). + test.
5. Coverage check — a `--report` flag on `fetch` or a `beam_pc.data` CLI that
   prints per-device photo/guide counts.
6. Update `pipeline.py` to use `ifixit_category` from the registry for the
   search query instead of `label.replace('_', ' ')` (one-line change once
   #1 exists).

## 6. Acceptance criteria

- [x] `devices.json` lists verified devices (51, broad corpus).
- [ ] `manifest.jsonl` covers ≥ 600 training images with train/val splits.
- [ ] `fetch_index.jsonl` covers every (device, repair_type) pair in the registry.
- [x] Re-running any fetch command does zero network I/O (all caches hit) —
      proven on the bulk dry run (re-run: 0 new entries, instant).
- [ ] `pytest` passes offline, including the new license-guard test.
- [ ] `python -m beam_pc.vision.train --epochs 1` runs end-to-end.
