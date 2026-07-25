"""CLI: search iFixit guides and cache them locally.

Single query / one guide (demo):
    python -m beam_pc.ifixit.fetch --query "iphone 13 battery" --limit 3
    python -m beam_pc.ifixit.fetch --guide-id 145896 --with-images

Bulk corpus download over data/devices.json (writes data/fetch_index.jsonl):
    python -m beam_pc.ifixit.fetch --all-devices --with-images --limit 5
    python -m beam_pc.ifixit.fetch --device iphone_13 --repair battery --with-images

Bulk runs are resumable: cached searches/guides/images are skipped on re-run,
and (guideid, device, repair) triples already in the index are not duplicated.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from beam_pc.config import DEVICES_JSON, FETCH_INDEX
from beam_pc.data.devices import Device, load_devices
from beam_pc.ifixit.client import IFixitClient
from beam_pc.ifixit.images import download_guide_images
from beam_pc.ifixit.models import ATTRIBUTION, Guide


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch repair guides from iFixit")
    parser.add_argument("--query", help="search text, e.g. 'iphone 13 battery'")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--guide-id", type=int, help="fetch one guide directly by id")
    parser.add_argument("--with-images", action="store_true", help="also download step images")
    parser.add_argument("--force", action="store_true", help="re-download images even if cached")
    parser.add_argument("--all-devices", action="store_true", help="bulk: every device in devices.json")
    parser.add_argument("--device", help="bulk: one device label, e.g. iphone_13")
    parser.add_argument("--repair", help="bulk: restrict to one repair type, e.g. battery")
    parser.add_argument("--devices-json", default=str(DEVICES_JSON))
    args = parser.parse_args()

    client = IFixitClient()

    if args.all_devices or args.device:
        _fetch_bulk(client, args)
        return

    if args.guide_id:
        _fetch_one(client, args.guide_id, args.with_images, args.force)
        return

    if not args.query:
        parser.error("provide --query, --guide-id, --device or --all-devices")

    results = client.search_guides(args.query, limit=args.limit)
    if not results:
        print("No guides found.")
        return
    for r in results:
        print(f"[{r.guideid}] {r.title}  ({r.difficulty or 'n/a'})")
        print(f"    {r.url}")
    print()
    _fetch_one(client, results[0].guideid, args.with_images, args.force)


def _fetch_one(client: IFixitClient, guideid: int, with_images: bool, force: bool = False) -> None:
    guide = client.guide(guideid)
    print(f"Guide: {guide.title}")
    print(f"Difficulty: {guide.difficulty or 'n/a'} | Steps: {len(guide.steps)}")
    if guide.tools:
        print(f"Tools: {', '.join(guide.tools)}")
    for step in guide.steps:
        head = step.title or (step.lines[0][:60] if step.lines else "")
        print(f"  {step.order}. {head}")
    if with_images:
        paths = download_guide_images(guide, force=force)
        print(f"Downloaded {len(paths)} images -> {paths[0].parent if paths else 'none'}")
    print(f"\n{ATTRIBUTION}")


# -- Bulk corpus download ----------------------------------------------------


def _fetch_bulk(client: IFixitClient, args: argparse.Namespace) -> None:
    devices = load_devices(Path(args.devices_json))
    if args.device:
        devices = [d for d in devices if d.label == args.device]
        if not devices:
            raise SystemExit(f"label {args.device!r} not found in {args.devices_json}")

    index_path = FETCH_INDEX
    done = _index_keys(index_path)
    new = 0
    for device in devices:
        repairs = [args.repair] if args.repair else device.repair_types
        for repair in repairs:
            query = f"{device.ifixit_category} {repair}"
            results = client.search_guides(query, limit=args.limit)
            print(f"{device.label} | {repair}: {len(results)} guides")
            for summary in results:
                key = (summary.guideid, device.label, repair)
                guide = client.guide(summary.guideid)
                n_images = 0
                if args.with_images:
                    n_images = len(download_guide_images(guide, force=args.force))
                if key not in done:
                    _index_append(index_path, guide, device, repair, args.with_images, n_images)
                    done.add(key)
                    new += 1
    print(f"\nfetch_index: {new} new entries ({len(done)} total) -> {index_path}")
    print(ATTRIBUTION)


def _index_keys(path: Path) -> set[tuple[int, str, str]]:
    keys: set[tuple[int, str, str]] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                e = json.loads(line)
                keys.add((int(e["guideid"]), e["device_label"], e["repair_type"]))
    return keys


def _index_append(path: Path, guide: Guide, device: Device, repair: str,
                  with_images: bool, n_images: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "guideid": guide.guideid,
        "title": guide.title,
        "device_label": device.label,
        "ifixit_category": device.ifixit_category,
        "repair_type": repair,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "with_images": with_images,
        "n_images": n_images,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    main()
