"""Runtime retrieval from the public iFixit API.

Hard rule: this layer is for per-request retrieval + local caching only.
iFixit's ToS prohibits using their data to train ML/AI models.
Content is CC BY-NC-SA 3.0 — attribute and link iFixit wherever shown.
"""

from beam_pc.ifixit.client import IFixitClient
from beam_pc.ifixit.models import Guide, GuideSummary, Step

__all__ = ["IFixitClient", "Guide", "GuideSummary", "Step"]
