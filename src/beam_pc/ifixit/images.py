"""Download guide step images for local viewing, with caching.

Reminder (CC BY-NC-SA 3.0): cached images remain iFixit content — attribute
them wherever displayed, and never feed them into a training set.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import requests

_IMG_EXT_RE = re.compile(r"\.(jpe?g|png|webp|gif)(?:[?/]|$)", re.IGNORECASE)


def _image_ext(url: str) -> str:
    """Real file extension from the URL; iFixit rendition URLs often end in
    '.full'/'.standard' etc., in which case default to .jpg."""
    m = _IMG_EXT_RE.search(url)
    return "." + m.group(1).lower() if m else ".jpg"

from beam_pc.config import IMAGE_DIR, ensure_dirs
from beam_pc.ifixit.models import Guide


def download_guide_images(
    guide: Guide,
    dest_dir: Path | None = None,
    rate_limit_s: float = 0.5,
    session: requests.Session | None = None,
    force: bool = False,
) -> list[Path]:
    """Fetch a guide's step images into dest_dir.

    Skips files already present unless force=True (e.g. re-downloading after
    the resolution preference changed).
    """
    ensure_dirs()
    dest = (dest_dir or IMAGE_DIR) / str(guide.guideid)
    dest.mkdir(parents=True, exist_ok=True)
    http = session or requests.Session()

    saved: list[Path] = []
    for i, url in enumerate(guide.image_urls):
        path = dest / f"{i:03d}{_image_ext(url)}"
        if path.exists() and not force:
            saved.append(path)
            continue
        resp = http.get(url, timeout=30)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        saved.append(path)
        time.sleep(rate_limit_s)
    return saved
