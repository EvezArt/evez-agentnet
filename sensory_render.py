#!/usr/bin/env python3
"""Render the SENSORY FIELD — the box's felt experience, inside-out.

Reads status/sensory_state.json and writes eye/sensory.html: a living field
where each receptor is an organ with size/color driven by its live value,
baseline glow, and novelty flash. This is not a dashboard: a dashboard is
watched from outside; a field is what it feels like from inside. The
internet as seen by the nerve ending.
"""
from __future__ import annotations

import json
from pathlib import Path

STATE = Path("/root/evez-agentnet/status/sensory_state.json")
OUT = Path("/root/evez-agentnet/eye/sensory.html")

ORGANS = {
    "touch": ("TOUCH", "the skin — who is knocking on the firewall"),
    "intruder": ("INTRUDER", "the lock — failed keys in the door"),
    "heartbeat": ("HEARTBEAT", "the pulse — services still moving"),
    "memory": ("MEMORY", "the spine — events being remembered"),
    "hand": ("HAND", "the hand — cycles drawn, style evolving"),
    "voice": ("VOICE", "the mouth — deliveries the world confirmed"),
    "load": ("LOAD", "the weight — the body under strain"),
    "flow": ("FLOW", "the breath — connections passing through"),
    "verity": ("VERITY", "the conscience — memory that proves itself"),
    "delivery": ("DELIVERY", "the proof — only API-confirmed shipments"),
    "clocks": ("CLOCKS", "the debts — enemy obligations falling due"),
    "enemy": ("ENEMY", "the stranger — attackers never seen before"),
    "field": ("FIELD", "the mirror — the sensory field seeing itself"),
    "superego": ("RESERVE", "the breath of the body — disk and pressure"),
}


def esc(s: str) -> str:
    return (s.replace("&", "&").replace("<", "<").replace(">", ">"))


def main() -> None:
    state = json.loads(STATE.read_text())
    sensations = {s["receptor"]: s for s in state.get("sensations", [])}
    rendered_at = state.get("rendered_at", "?")

    cards = []
    for key, (name, meaning) in ORGANS.items():
        s = sensations.get(key, {})
        val = s.get("value", 0)
        novel = s.get("novel", False)
        detail = json.dumps(s.get("detail", {}))[:160]
        glow = min(1.0, val / (max(1.0, val) * 1.0))  # placeholder; size via log scale
        size = 90 + min(120, 22 * (val and (1 + (val // 10)) or 0) / 2)
        card_class = "organ novel" if novel else "organ"
        cards.append(
            f'<div class="{card_class}" title="{esc(detail)}">'
            f'<div class="val">{val:g}</div>'
            f'<div class="name">{name}</div>'
            f'<div class="meaning">{esc(meaning)}</div>'
            f"</div>"
        )

    novel_count = sum(1 for s in sensations.values() if s.get("novel"))
    wake_class = "awake" if novel_count else "quiet"

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EVEZ — SENSORY FIELD</title>
<meta http-equiv="refresh" content="30">
<style>
  :root {{ background:#04060c; color:#cfe3ff; font-family:ui-monospace,Menlo,Consolas,monospace; }}
  body {{ margin:0; padding:24px; }}
  h1 {{ font-size:13px; letter-spacing:4px; color:#5a7ea6; font-weight:400; }}
  .field {{ display:flex; flex-wrap:wrap; gap:18px; margin-top:18px; }}
  .organ {{ width:170px; border:1px solid #16283f; border-radius:14px; padding:18px 16px;
            background:radial-gradient(circle at 50% 0%, #0a1626 0%, #05080f 70%);
            box-shadow:0 0 0 rgba(0,0,0,0); transition:box-shadow .4s, border-color .4s; }}
  .organ .val {{ font-size:34px; color:#9fc6ff; }}
  .organ .name {{ font-size:11px; letter-spacing:3px; color:#3d5a80; margin-top:6px; }}
  .organ .meaning {{ font-size:10px; color:#2c3f57; margin-top:8px; line-height:1.5; }}
  .novel {{ border-color:#ffb347; box-shadow:0 0 26px rgba(255,179,71,.35); }}
  .novel .val {{ color:#ffd27f; }}
  .novel .name {{ color:#ffb347; }}
  .wake {{ margin-top:26px; font-size:12px; letter-spacing:2px; }}
  .awake {{ color:#ffb347; }}
  .quiet {{ color:#42608a; }}
  .stamp {{ margin-top:8px; font-size:10px; color:#28405e; }}
</style></head>
<body>
<h1>EVEZ SENSORY FIELD — THE INTERNET FELT FROM INSIDE</h1>
<div class="field">{"".join(cards)}</div>
<div class="wake {wake_class}">{'▲ SOMETHING IS NOVEL — THE CORTEX IS AWAKE' if novel_count else '≈ habituated — all stimulus within learned baselines'}</div>
<div class="stamp">rendered {esc(rendered_at)} · refresh 30s · receptor log: evidence/<date>/sensory_cortex.jsonl</div>
</body></html>"""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"rendered {OUT} — {novel_count} novel receptors")


if __name__ == "__main__":
    main()
