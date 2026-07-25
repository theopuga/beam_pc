"""Offline tests: model parsing + client behavior with a stubbed session."""

import json

from beam_pc.ifixit.client import IFixitClient
from beam_pc.ifixit.models import Guide, GuideSummary

GUIDE_JSON = {
    "guideid": 145896,
    "title": "iPhone 13 Battery Replacement",
    "url": "https://www.ifixit.com/Guide/iPhone+13+Battery+Replacement/145896",
    "category": "iPhone 13",
    "subject": "Battery",
    "difficulty": "Moderate",
    "introduction_raw": "Swap a dead battery.",
    "tools": [{"text": "Spudger"}, {"text": "P2 Pentalobe Screwdriver"}],
    "parts": [{"text": "iPhone 13 Battery"}],
    "steps": [
        {
            "orderby": 1,
            "title": "Remove the pentalobe screws",
            "lines": [{"text_raw": "Power off the phone."}, {"text_raw": "Remove the two 6.7 mm screws."}],
            "media": {"data": [{"standard": "https://assets.cdn.ifixit.com/std1.jpg", "large": "https://assets.cdn.ifixit.com/lrg1.jpg"}]},
        },
        {
            "orderby": 2,
            "title": "",
            "lines": [{"text_raw": "Lift the display."}],
            "media": {"data": []},
        },
    ],
}

SEARCH_JSON = {
    "results": [
        {"dataType": "guide", "guideid": 145896, "title": "iPhone 13 Battery Replacement",
         "url": "https://www.ifixit.com/Guide/x/145896", "category": "iPhone 13",
         "subject": "Battery", "difficulty": "Moderate", "summary": "..."},
        {"dataType": "wiki", "guideid": 1, "title": "not a guide"},
    ]
}


class StubResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class StubSession:
    def __init__(self, payload):
        self.payload = payload
        self.headers = {}
        self.requests = []

    def get(self, url, params=None, timeout=None):
        self.requests.append((url, params))
        return StubResponse(self.payload)


def test_guide_parsing():
    g = Guide.from_api(GUIDE_JSON)
    assert g.guideid == 145896
    assert g.difficulty == "Moderate"
    assert g.tools == ["Spudger", "P2 Pentalobe Screwdriver"]
    assert len(g.steps) == 2
    assert g.steps[0].lines[1] == "Remove the two 6.7 mm screws."
    # parser must prefer the largest rendition available (large over standard)
    assert g.image_urls == ["https://assets.cdn.ifixit.com/lrg1.jpg"]
    assert "CC BY-NC-SA" in g.attribution


def test_search_filters_to_guides():
    client = IFixitClient(rate_limit_s=0, cache_dir=None, session=StubSession(SEARCH_JSON))
    results = client.search_guides("iphone battery")
    assert results == [GuideSummary(guideid=145896, title="iPhone 13 Battery Replacement",
                                    url="https://www.ifixit.com/Guide/x/145896",
                                    category="iPhone 13", subject="Battery",
                                    difficulty="Moderate", summary="...")]


def test_guide_caches_to_disk(tmp_path):
    session = StubSession(GUIDE_JSON)
    client = IFixitClient(rate_limit_s=0, cache_dir=tmp_path, session=session)

    client.guide(145896)
    assert (tmp_path / "145896.json").exists()
    assert json.loads((tmp_path / "145896.json").read_text())["title"] == "iPhone 13 Battery Replacement"

    # second call must hit cache, not network
    client.guide(145896)
    assert len(session.requests) == 1


def test_search_caches_to_disk(tmp_path):
    session = StubSession(SEARCH_JSON)
    # cache_dir is the *guides* dir; searches land in the sibling "searches" dir
    client = IFixitClient(rate_limit_s=0, cache_dir=tmp_path / "guides", session=session)

    results = client.search_guides("iphone battery", limit=3)
    assert len(session.requests) == 1
    cached = list((tmp_path / "searches").glob("*.json"))
    assert len(cached) == 1

    # second identical call must hit cache, not network, with identical results
    assert client.search_guides("iphone battery", limit=3) == results
    assert len(session.requests) == 1
