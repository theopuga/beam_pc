"""CLI: search iFixit guides and cache them locally.

    python -m beam_pc.ifixit.fetch --query "iphone 13 battery" --limit 3
    python -m beam_pc.ifixit.fetch --guide-id 145896 --with-images
"""

from __future__ import annotations

import argparse

from beam_pc.ifixit.client import IFixitClient
from beam_pc.ifixit.images import download_guide_images
from beam_pc.ifixit.models import ATTRIBUTION


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch repair guides from iFixit")
    parser.add_argument("--query", help="search text, e.g. 'iphone 13 battery'")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--guide-id", type=int, help="fetch one guide directly by id")
    parser.add_argument("--with-images", action="store_true", help="also download step images")
    parser.add_argument("--force", action="store_true", help="re-download images even if cached")
    args = parser.parse_args()

    client = IFixitClient()

    if args.guide_id:
        _fetch_one(client, args.guide_id, args.with_images, args.force)
        return

    if not args.query:
        parser.error("provide --query or --guide-id")

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


if __name__ == "__main__":
    main()
