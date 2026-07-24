"""Dataclasses for iFixit API payloads. Parsing is defensive: the API
has evolved over the years, so missing fields degrade to defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ATTRIBUTION = "Repair guide content © iFixit, licensed CC BY-NC-SA 3.0 — https://www.ifixit.com"


@dataclass
class GuideSummary:
    guideid: int
    title: str
    url: str
    category: str = ""
    subject: str = ""
    difficulty: str = ""
    summary: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "GuideSummary":
        return cls(
            guideid=int(data.get("guideid", 0)),
            title=data.get("title", ""),
            url=data.get("url", ""),
            category=data.get("category", "") or "",
            subject=data.get("subject", "") or "",
            difficulty=data.get("difficulty", "") or "",
            summary=data.get("summary", "") or "",
        )


@dataclass
class Step:
    order: int
    title: str
    lines: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)


@dataclass
class Guide:
    guideid: int
    title: str
    url: str
    category: str = ""
    subject: str = ""
    difficulty: str = ""
    introduction: str = ""
    steps: list[Step] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)
    attribution: str = ATTRIBUTION

    @property
    def image_urls(self) -> list[str]:
        urls: list[str] = []
        for step in self.steps:
            urls.extend(step.image_urls)
        return urls

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Guide":
        steps = []
        for i, raw_step in enumerate(data.get("steps") or []):
            lines = [
                line.get("text_raw", "")
                for line in (raw_step.get("lines") or [])
                if line.get("text_raw")
            ]
            image_urls = _extract_image_urls(raw_step.get("media"))
            steps.append(
                Step(
                    order=int(raw_step.get("orderby", i + 1)),
                    title=raw_step.get("title", "") or "",
                    lines=lines,
                    image_urls=image_urls,
                )
            )
        return cls(
            guideid=int(data.get("guideid", 0)),
            title=data.get("title", ""),
            url=data.get("url", ""),
            category=data.get("category", "") or "",
            subject=data.get("subject", "") or "",
            difficulty=data.get("difficulty", "") or "",
            introduction=data.get("introduction_raw", "") or "",
            steps=steps,
            tools=[t.get("text", "") for t in (data.get("tools") or []) if t.get("text")],
            parts=[p.get("text", "") for p in (data.get("parts") or []) if p.get("text")],
        )


# iFixit image objects carry many renditions; grab the largest available.
_SIZE_PREFERENCE = (
    "original", "huge", "large", "medium",
    "440x330", "standard", "200x150", "140x105", "thumbnail", "mini",
)


def _extract_image_urls(media: Any) -> list[str]:
    """Pull the highest-resolution image URLs out of a step's media blob."""
    urls: list[str] = []
    if not isinstance(media, dict):
        return urls
    for image in media.get("data") or []:
        if not isinstance(image, dict):
            continue
        for size in _SIZE_PREFERENCE:
            if image.get(size):
                urls.append(image[size])
                break
    return urls
