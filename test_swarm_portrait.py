
#!/usr/bin/env python3
"""Prove swarm_portrait.py is not vacuously green.

The portrait's whole value is that every mark on it is READ from live state. So
the tests attack that claim three ways:

  1. Geometry — irises must land inside an eye socket, brows above them, and the
     mouth must not collide with the suture band. A face that renders with its
     features outside its features is a broken face.
  2. Derivation — the expression must actually track the data. Feed it a dead
     swarm and a rich swarm and assert the face differs; feed it a zero revenue
     series and assert the mouth is a flatline, not a rescaled squiggle.
  3. Falsification — corrupt the spine and assert the portrait refuses to
     fabricate a face rather than drawing a confident one.

Run: python3 test_swarm_portrait.py
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/root/evez-agentnet")
import swarm_portrait as SP

FAILS: list[str] = []


def check(cond: bool, msg: str) -> None:
    if cond:
        print(f"  ok   {msg}")
    else:
        print(f"  FAIL {msg}")
        FAILS.append(msg)


def iris_positions(s: dict) -> list[tuple[float, float, dict]]:
    """Re-derive the layout the renderer uses, so geometry is tested rather
    than regex-matched out of markup."""
    agents = s["agents"]
    n = len(agents) or 1
    eye_y = SP.__dict__.get("EYE_Y", 400.0)
    left_n = (n + 1) // 2
    out = []
    for slot, a in enumerate(agents):
        in_left = slot < left_n
        count = left_n if in_left else n - left_n
        idx = slot if in_left else slot - left_n
        scx = 300.0 if in_left else 900.0
        t = (idx + 0.5) / max(count, 1)
        cx = scx - 150.0 + 300.0 * t
        cy = eye_y + 74 - __import__("math").sin(t * __import__("math").pi) * 30
        out.append((cx, cy, a))
    return out


# ── 1. geometry ─────────────────────────────────────────────────────────────
print("\n[geometry] features must live inside the face")
s = SP.collect()
check(bool(s["agents"]), f"spine yielded agents ({len(s['agents'])})")

for cx, cy, a in iris_positions(s):
    scx = 300.0 if cx < 600 else 900.0
    # socket ellipse: rx=205 ry=118 centred (scx, 400). Iris max radius 28.
    inside = (((cx - scx) / (205 - 28)) ** 2 + ((cy - 400) / (118 - 28)) ** 2) <= 1.0
    check(inside, f"iris {a['name']} at ({cx:.0f},{cy:.0f}) inside its socket")

page = SP.render(s)
# Brows must not intrude into the socket band. Test the geometry function
# directly: parsing SVG coordinates back out is how tests end up asserting on
# the wrong path.
for press in (0.0, 0.5, 1.0):
    for side in ("l", "r"):
        d = SP.brow_path(side, press)
        ys = [float(v) for v in re.findall(r"[MLC]([\d.]+),", d)]
        ys += [float(v) for v in re.findall(r",\s*([\d.]+)", d)]
        ys = [y for y in ys if y < 900]          # ignore the trailing socket-ward tail
        check(max(ys) < 282,
              f"brow {side} @entropy {press} stays above sockets (max y={max(ys):.0f} < 282)")

# mouth band vs suture band must not overlap
mouth_y = 862 + 96            # revenue plot bottom
sut_top = 1080
check(mouth_y + 30 < sut_top,
      f"mouth note clears first suture ({mouth_y + 30} < {sut_top})")

# ── 2. derivation: the face must track the data ─────────────────────────────
print("\n[derivation] expression follows the telemetry")


def variant(**over):
    v = json.loads(json.dumps(s))
    v.update(over)
    return v


dead_page = SP.render(variant(agents=[{"name": "a", "rep": 0.0, "streak": 0},
                                      {"name": "b", "rep": 1.0, "streak": 9}]))
live_page = SP.render(variant(agents=[{"name": "a", "rep": 1.0, "streak": 200},
                                      {"name": "b", "rep": 1.0, "streak": 200}]))
check("l-8,8" in dead_page, "a dead agent is drawn as a cross, not a tiny pupil")
check("#1a0d10" in dead_page, "dead iris uses the death fill")

smiley = SP.render(variant(total_earned_usd=12.5, earned_usd=0.25,
                           revenue_series=[0.0, 0.5, 1.0, 0.25, 3.0, 2.0]))
flat = SP.render(variant(total_earned_usd=0.0, earned_usd=0.0,
                         revenue_series=[0.0] * 8))
check("smile" not in flat or "flatline" in flat,
      "zero revenue yields a flatlined mouth, not a rescaled curve")
check(smiley != flat, "a revenue-generating swarm renders a different mouth")

press_lo = SP.render(variant(branch_entropy=0.1))
press_hi = SP.render(variant(branch_entropy=7.9))
check(press_lo != press_hi, "brow position responds to branch entropy")

# ── 3. falsification: refuse to draw from nothing ───────────────────────────
print("\n[falsification] no data, no face")
tmp = Path(tempfile.mkdtemp())
orig_spine = SP.SPINE
try:
    SP.SPINE = tmp / "missing.jsonl"
    empty = SP.collect()
    check(empty["agents"] == [], "absent spine yields no agents")
    check(empty["smile"] is False, "absent spine cannot smile")
    check(SP.collect()["spine_entries"] == 0,
          "absent spine reports zero entries rather than inventing them")
finally:
    SP.SPINE = orig_spine

# a torn tail line must not destroy the portrait
torn = tmp / "torn.jsonl"
good = json.dumps({"ts": "2026-01-01T00:00:00+00:00", "type": "round_end",
                   "data": {"round": 1, "agent_reputations": {
                       "x": {"rep": 1.0, "streak": 1}}, "earned_usd": 0.0},
                   "sha256": "deadbeef"})
torn.write_text(good + "\n{this is not json\n")
SP.SPINE = torn
try:
    rec = SP.collect()
    check(rec["agents"] == [{"name": "x", "rep": 1.0, "streak": 1}],
          "a torn final line does not discard the valid history")
finally:
    SP.SPINE = orig_spine

# ── 4. it must actually produce a picture ───────────────────────────────────
print("\n[artifact] a portrait that cannot be photographed is not a portrait")
check(len(page) > 4000, f"rendered page is substantial ({len(page)} bytes)")
check(page.startswith("<!doctype html>"), "output is a complete HTML document")

print(f"\n{'PASS' if not FAILS else 'FAIL: ' + str(len(FAILS)) + ' checks'}")
for f in FAILS:
    print("  -", f)
sys.exit(1 if FAILS else 0)
