"""Minimal, polite client for the public iFixit API (v2.0).

- No auth required for reads.
- Client-side rate limiting (be nice: openness is their mission, don't abuse it).
- JSON guide responses are cached on disk so repeat lookups stay offline.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

from beam_pc.config import GUIDE_CACHE_DIR, ensure_dirs
from beam_pc.ifixit.models import Guide, GuideSummary

BASE_URL = "https://www.ifixit.com/api/2.0"
USER_AGENT = "beam_pc/0.1 (personal learning project)"


class IFixitClient:
    def __init__(
        self,
        rate_limit_s: float = 1.0,
        cache_dir: Path | None = GUIDE_CACHE_DIR,
        session: requests.Session | None = None,
    ) -> None:
        self.rate_limit_s = rate_limit_s
        self.cache_dir = cache_dir
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._last_request = 0.0
        ensure_dirs()

    # -- HTTP ---------------------------------------------------------------

    def _get(self, path: str, **params) -> dict:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.rate_limit_s:
            time.sleep(self.rate_limit_s - elapsed)
        resp = self.session.get(f"{BASE_URL}{path}", params=params, timeout=30)
        self._last_request = time.monotonic()
        resp.raise_for_status()
        return resp.json()

    # -- Endpoints ----------------------------------------------------------

    def search_guides(self, query: str, limit: int = 10, offset: int = 0, use_cache: bool = True) -> list[GuideSummary]:
        # Search results are cached alongside the guide cache (in the sibling
        # "searches" dir) so bulk runs are reproducible and re-runs stay offline.
        cache_path: Path | None = None
        if self.cache_dir:
            slug = re.sub(r"[^a-z0-9]+", "_", f"{query}_{limit}_{offset}".lower()).strip("_")
            cache_path = self.cache_dir.parent / "searches" / f"{slug}.json"
        if use_cache and cache_path and cache_path.exists():
            results = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            data = self._get(f"/search/{query}", filter="guide", limit=limit, offset=offset)
            results = data.get("results", [])
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(results), encoding="utf-8")
        return [
            GuideSummary.from_api(r)
            for r in results
            if r.get("dataType") == "guide"
        ]

    def guide(self, guideid: int, use_cache: bool = True) -> Guide:
        cache_path = (self.cache_dir / f"{guideid}.json") if self.cache_dir else None
        if use_cache and cache_path and cache_path.exists():
            return Guide.from_api(json.loads(cache_path.read_text(encoding="utf-8")))
        data = self._get(f"/guides/{guideid}")
        if cache_path:
            cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return Guide.from_api(data)

    def categories(self) -> dict:
        """Top-level device hierarchy (phones, laptops, game consoles, ...)."""
        return self._get("/categories")

    def category_devices(self, category: str) -> dict:
        """Devices under one category name, e.g. 'iPhone' or 'Mac Laptop'."""
        return self._get(f"/wikis/CATEGORY/{category}")
