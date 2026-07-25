# Data plan: fetching & organization

Goal: get from "empty `data/dataset/` + one cached guide" to enough data to train
the v1 device classifier and demo the end-to-end pipeline.

Two hard constraints (already encoded in the codebase):

- **iFixit images must never enter the training set** (CC BY-NC-SA + their ToS
  bans ML training). They are lookup/display content only.
- Tests stay offline; all network happens through `IFixitClient`.

---

## 1. What data we actually need

| # | Data | Purpose | Source | Status |
|---|------|---------|--------|--------|
| A | Training images (~20 device models, 30–50 photos each) | Train `vision.train` classifier | Own photos / permissively licensed | **missing — the blocker** |
| B | Guide corpus: cached guide JSON per device × repair type | Retrieval side of the pipeline; offline demos | iFixit API via `IFixitClient` | 1 guide cached |
| C | Device taxonomy (label registry) | Align dataset folder names ↔ model classes ↔ iFixit category names | Derived from `/categories` + manual shortlist | missing |

C comes first: without it, A gets inconsistent folder names and B can't be
fetched systematically.

---

## 2. Review: how fetch organizes data today

```
data/
  cache/guides/<guideid>.json     # raw guide payloads, keyed by id        ✅ good
  images/<guideid>/000.jpg        # guide step images, sequential names    ⚠️ ok, see 2.5
  dataset/<device_label>/*.jpg    # training images                        ✅ good split, empty
  dataset/manifest.jsonl          # index over dataset/                    ⚠️ code exists, file missing
```

What works:

- **License separation is correct**: `images/` (iFixit, view-only) vs `dataset/`
  (training). Keep this wall; add an automated check (§4, phase 3).
- Guide JSON cache is simple and effective; `fetch --guide-id` is idempotent.
- Rate limiting + defensive parsing already in place.

Gaps found:

1. **No canonical device labels.** Dataset folders are freeform, and
   `pipeline.py` builds the search query with `label.replace('_', ' ')`.
   If the folder is `iphone_13` but iFixit's category is `iPhone 13`, we get
   lucky; if it's `thinkpad_t480`, we may not. Labels need to be chosen *from*
   iFixit category names, not invented.
2. **`categories()` / `category_devices()` are unused.** Nothing enumerates the
   iFixit device universe, so we can't verify a shortlist label actually maps
   to guides before collecting photos for it.
3. **Search results are not cached.** Only full guides are. Every CLI run
   re-hits `/search`, and runs aren't reproducible (top hit can change).
4. **No fetch index.** Nothing records what was fetched, when, or for which
   device — no way to audit coverage ("which of my 20 devices have guides
   cached?") or re-fetch stale entries.
5. **Image naming loses step association.** `000.jpg` is the i-th image in the
   flattened guide, not step N image M. Fine for a viewer; acceptable for now,
   but note it in the index (store `guideid -> step order -> file` later only
   if the UI needs it). *Decision: leave naming as-is for v1.*
6. **`fetch` CLI fetches only `results[0]`.** Good demo default, useless for
   building a corpus. Needs a bulk mode.
7. **No split assignment.** `scan_dataset_dir` defaults everything to `train`;
   `manifest.jsonl` has never been generated.

---

## 3. Proposed layout (minimal changes)

```
data/
  cache/
    guides/<guideid>.json            # keep as-is
    searches/<query-slug>.json       # NEW: cached search results (GuideSummary dicts)
    categories/<category-slug>.json  # NEW: device listings per iFixit category
  images/<guideid>/NNN.jpg           # keep as-is (iFixit content, never training)
  dataset/<device_label>/*.jpg       # keep as-is (own photos only)
  dataset/manifest.jsonl             # generated, not hand-edited
  devices.json                       # NEW: label registry (source-controlled, see below)
  fetch_index.jsonl                  # NEW: one line per fetched guide
```

**`devices.json`** (lives in `data/`; small enough to commit if we want it
reproducible, gitignore decision deferred):

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

### Phase 0 — Device shortlist (manual, ~30 min)
- List ~20 devices you can physically photograph (own/family/friends' phones,
  laptops, consoles). This is a real-world constraint, not a code decision.
- For each candidate, run `category_devices()` once to confirm the iFixit
  category name and that guides exist. Write results into `devices.json`.
- Output: committed `devices.json` with verified `ifixit_category` per label.

### Phase 1 — Training photos (the slow, manual part)
- 30–50 photos per device: front/back/edges, varied lighting and backgrounds,
  a few with cases on/off. Phone camera is fine; no augmentation heroics yet.
- Drop into `data/dataset/<label>/` (any filename).
- Regenerate the manifest: extend `scan_dataset_dir` (or a small CLI) to assign
  splits deterministically (e.g. every 5th image per class → `val`), then
  `write_manifest`.
- Output: `data/dataset/` populated + `manifest.jsonl` with train/val splits.

### Phase 2 — Guide corpus (scripted, polite)
- Extend `fetch` CLI with bulk mode:
  `python -m beam_pc.ifixit.fetch --device iphone_13 --repair battery --limit 5 --with-images`
  and `--all-devices` to loop over `devices.json`.
- For each (device, repair_type): search (cached), fetch top-N full guides
  (cached), append to `fetch_index.jsonl`. Images optional — only needed for
  UI/demo, they're the bulk of the bytes.
- Budget: 20 devices × 2 repair types × 5 guides ≈ 200 guide fetches ≈ fine at
  1 req/s (~10 min including images at 0.5 s/img).
- Output: populated `cache/guides/`, `fetch_index.jsonl` with full coverage.

### Phase 3 — Validation
- Coverage report (script or CLI flag): photos per class vs `min_photos`,
  cached guides per device × repair type. Fail loudly on gaps.
- License guard: assert no file under `data/images/` is referenced by
  `manifest.jsonl` (cheap path-prefix check; add as a test).
- `pytest` still green, still offline.

---

## 5. Code changes needed (small, in order)

1. `beam_pc/data/devices.py` — load/validate `devices.json` (stdlib
   dataclass, same style as `manifest.py`). + test.
2. `client.search_guides` — add on-disk cache for search results (keyed by
   query+limit slug), mirroring the existing guide cache. + test with
   StubSession.
3. `fetch.py` — bulk mode (`--device`/`--repair`/`--all-devices`) writing to
   `fetch_index.jsonl`; keep current `--query`/`--guide-id` behavior untouched.
4. `manifest.py` — deterministic split assignment in `scan_dataset_dir` (or a
   `--val-every N` flag on a tiny CLI). + test.
5. Coverage check — a `--report` flag on `fetch` or a `beam_pc.data` CLI that
   prints per-device photo/guide counts.
6. Update `pipeline.py` to use `ifixit_category` from the registry for the
   search query instead of `label.replace('_', ' ')` (one-line change once
   #1 exists).

## 6. Acceptance criteria

- [ ] `devices.json` lists ~20 verified devices.
- [ ] `manifest.jsonl` covers ≥ 600 training images with train/val splits.
- [ ] `fetch_index.jsonl` covers every (device, repair_type) pair in the registry.
- [ ] Re-running any fetch command does zero network I/O (all caches hit).
- [ ] `pytest` passes offline, including the new license-guard test.
- [ ] `python -m beam_pc.vision.train --epochs 1` runs end-to-end.
