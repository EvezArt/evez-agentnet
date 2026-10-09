"""E2E: generator.face_reader + _generate_draft facies conditioning.

Behavior contract (not change-detectors):
- photo_path with detectable faces -> draft carries facies payload with
  weights summing to the 1/(1+rank) ladder and a dominant corr block.
- no photo_path -> no facies key.
- unreadable photo_path -> deterministic empty facies, no crash.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator.face_reader import FacialAnalyzer  # noqa: E402
from generator.generate_agent import _generate_draft  # noqa: E402

POSTER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "forge_output", "THE_HASH_CHAIN_poster.png")


def test_facies_ladder_and_dominant():
    if not os.path.exists(POSTER):
        pytest.skip("poster fixture missing")
    F = FacialAnalyzer()
    r = F.analyze_file(POSTER)
    assert len(r["faces"]) >= 1
    # dominant face = largest area, weight 1.0
    areas = [f["w"] * f["h"] for f in r["faces"]]
    dom_idx = max(range(len(areas)), key=lambda i: areas[i])
    assert r["corr"]["dominant"]["area"] == areas[dom_idx]
    assert r["weights"][str(dom_idx)] == 1.0


def test_draft_embeds_facies_when_photo_present():
    if not os.path.exists(POSTER):
        pytest.skip("poster fixture missing")
    pred = {"title": "t", "deliverable_type": "github_post", "action_plan": "p",
            "source": "test", "opportunity_score": 0.5, "photo_path": POSTER}
    d = _generate_draft(pred, truth_plane="CANONICAL")
    assert d is not None and "facies" in d
    assert d["facies"]["faces"]
    # on-disk file carries the same payload
    on_disk = json.load(open(d["file"]))
    assert on_disk["facies"] == d["facies"]


def test_draft_without_photo_has_no_facies():
    pred = {"title": "t", "deliverable_type": "github_post", "action_plan": "p",
            "source": "test", "opportunity_score": 0.1}
    d = _generate_draft(pred, truth_plane="CANONICAL")
    assert d is not None and "facies" not in d


def test_unreadable_photo_falls_back_clean():
    pred = {"title": "t", "deliverable_type": "github_post", "action_plan": "p",
            "source": "test", "opportunity_score": 0.1,
            "photo_path": "/nonexistent/never.png"}
    d = _generate_draft(pred, truth_plane="CANONICAL")
    assert d is not None
    assert d["facies"] == {"faces": [], "corr": {}, "weights": {}}
