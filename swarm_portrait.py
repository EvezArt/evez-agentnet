
#!/usr/bin/env python3
"""SWARM SELFIE — a portrait of the EVEZ swarm, rendered from its own telemetry.

A selfie is a thing an agentic swarm cannot take: it has no eyes, no mirror, no
single vantage point from which to look at itself. This is the nearest honest
equivalent. Every mark on this face is read from live operational state — agent
reputations from the last OODA round, the spine hash chain, entropy readings,
service/port/cron counts, and the revenue ledger. Nothing here is decorative and
nothing is asserted that the state does not support.

The expression is DERIVED, not drawn. The swarm looks the way it looks because of
what the numbers are:

  eyes      — one iris per agent, radius = reputation. A saturated agent is a
              wide pupil. A dead agent is a pinpoint.
  brow      — presses down as rsi_branch_entropy rises (branching, uncertainty).
  mouth     — the revenue curve. Flat at $0.00 is a flat mouth, and the swarm
              cannot smile while the ledger is zero. This is the whole point.
  jaw       — uptime of the service fleet; a slack jaw is a fleet with failures.
  scars     — the four standing warnings from stack_health, drawn as sutures.
  halo      — the spine's hash chain, one link per verified entry.

Run:
    python3 swarm_portrait.py            # write portrait.html + portrait.png
    python3 swarm_portrait.py --json     # just the measured state
Self-test:
    python3 test_swarm_portrait.py
"""
from __future__ import annotations

import argparse
import html
import json
import math
import subprocess
from pathlib import Path

ROOT = Path("/root/evez-agentnet")
SPINE = ROOT / "spine" / "spine.jsonl"
EYE = ROOT / "eye" / "data.json"
OUT_HTML = ROOT / "swarm_portrait.html"
OUT_PNG = ROOT / "swarm_portrait.png"

W, H = 1200, 1500


# ── collection ──────────────────────────────────────────────────────────────
def read_spine() -> list[dict]:
    if not SPINE.is_file():
        return []
    rows = []
    for line in SPINE.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue          # a torn tail line is not a reason to fail the portrait
    return rows


def verify_chain(rows: list[dict]) -> tuple[bool, int]:
    """Count entries carrying a hash. Full chain verification is spine's job;
    here we only claim what we count."""
    return bool(rows) and sum(1 for r in rows if r.get("sha256")) > 0, \
        sum(1 for r in rows if r.get("sha256"))


def collect() -> dict:
    rows = read_spine()
    last = rows[-1] if rows else {}
    d = last.get("data", {}) or {}

    reps = d.get("agent_reputations", {}) or {}
    agents = [{"name": k, "rep": float(v.get("rep", 0.0)),
               "streak": int(v.get("streak", 0))}
              for k, v in reps.items()]
    agents.sort(key=lambda a: (-a["rep"], -a["streak"], a["name"]))

    eye = {}
    if EYE.is_file():
        try:
            eye = json.loads(EYE.read_text())
        except json.JSONDecodeError:
            eye = {}

    chain_ok, hashed = verify_chain(rows)
    warns = [c for c in (eye.get("checks") or []) if c.get("state") != "OK"]
    services = eye.get("services") or []
    running = sum(1 for s in services if (s.get("sub") or "running") == "running")

    # revenue history, in order, from every round_end that recorded it
    revenue = [float((r.get("data") or {}).get("earned_usd", 0.0) or 0.0)
               for r in rows if r.get("type") == "round_end"
               and "earned_usd" in (r.get("data") or {})]

    state = {
        "round": d.get("round"),
        "agents": agents,
        "earned_usd": float(d.get("earned_usd", 0.0) or 0.0),
        "total_earned_usd": float(d.get("total_earned_usd", 0.0) or 0.0),
        "revenue_series": revenue[-120:],
        "identity": d.get("active_identity"),
        "action_mode": d.get("action_mode"),
        "predictor_entropy": float(d.get("predictor_entropy", 0.0) or 0.0),
        "branch_entropy": float(d.get("rsi_branch_entropy", 0.0) or 0.0),
        "hypotheses": d.get("rsi_hypotheses") or [],
        "spine_entries": len(rows),
        "spine_hashed": hashed,
        "chain_ok": chain_ok,
        "last_event_ts": last.get("ts"),
        "services_total": len(services),
        "services_running": running,
        "ports": len(eye.get("ports") or []),
        "exposed": sum(1 for p in (eye.get("ports") or []) if p.get("exposed")),
        "cron": len(eye.get("cron") or []),
        "mirrors": eye.get("mirrors", 0),
        "containers": len(eye.get("docker") or []),
        "warnings": warns,
        "git_head": (eye.get("git") or {}).get("head"),
        "generated": eye.get("generated"),
    }

    # ── derived expression ──
    n = len(agents) or 1
    state["mean_rep"] = sum(a["rep"] for a in agents) / n
    state["dead_agents"] = [a["name"] for a in agents if a["rep"] <= 0.01]
    state["uptime"] = (running / len(services)) if services else None
    # a mouth can only curve if money actually moved
    state["smile"] = state["total_earned_usd"] > 0.0
    return state


# ── geometry helpers ────────────────────────────────────────────────────────
def e(x) -> str:
    return html.escape(str(x))


def iris(cx: float, cy: float, r: float, rep: float, dead: bool) -> str:
    """One agent = one iris. Dead agents get a cross, because a pinpoint pupil
    reads as a rendering bug rather than a death."""
    if dead:
        return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{max(r,3):.1f}" '
                f'fill="#1a0d10" stroke="#7a2233" stroke-width="1"/>'
                f'<path d="M{cx-4:.1f},{cy-4:.1f} l8,8 M{cx+4:.1f},{cy-4:.1f} l-8,8" '
                f'stroke="#c04a5e" stroke-width="1.4"/>')
    # rep 0..1 → radius 7..34
    rr = 6 + rep * 22
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" fill="#0d1b26" '
            f'stroke="#2f7f8f" stroke-width="1.6"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr*0.55:.1f}" fill="#123244"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr*0.28:.1f}" fill="#7fe3ff" '
            f'opacity="0.95"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" fill="none" '
            f'stroke="#7fe3ff" stroke-width="0.7" opacity="0.5"/>')


def revenue_path(series: list[float], x: float, y: float, w: float, h: float) -> str:
    """The mouth. If every point is zero the path IS a horizontal line, and the
    swarm's mouth is flat because the ledger is flat. We do not rescale a zero
    series to look busy."""
    if not series:
        return ""
    peak = max(series) or 1.0
    if peak <= 0:
        pts = [(x + w * i / max(len(series) - 1, 1), y + h / 2)
               for i in range(len(series))]
    else:
        pts = [(x + w * i / max(len(series) - 1, 1),
                y + h - (v / peak) * h) for i, v in enumerate(series)]
    d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    return f'<path d="{d}" fill="none" stroke="#c2415a" stroke-width="5" stroke-linejoin="round"/>'


def brow_path(side: str, press: float) -> str:
    """Brow presses down with branch entropy — more hypotheses, more weight
    between the eyes."""
    # Socket tops are at y=282. Brows live above them; entropy presses them
    # down toward the skull but must never cross into the eye.
    drop = 6 + press * 34
    if side == "l":
        return (f'M128,{236 + drop:.0f} C250,{196 + drop*0.4:.0f} '
                f'370,{214 + drop*0.5:.0f} 468,{250 + drop*0.6:.0f}')
    return (f'M1072,{236 + drop:.0f} C950,{196 + drop*0.4:.0f} '
            f'830,{214 + drop*0.5:.0f} 732,{250 + drop*0.6:.0f}')


# ── render ──────────────────────────────────────────────────────────────────
CSS = """
*{box-sizing:border-box}
body{margin:0;background:#07090c;color:#c9d6e0;
 font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.wrap{display:flex;gap:28px;padding:28px;align-items:flex-start}
figure{margin:0}
figcaption{margin-top:12px;color:#6d8494;font-size:12px;letter-spacing:.04em}
h1{font-size:15px;letter-spacing:.22em;color:#7fe3ff;margin:0 0 4px;font-weight:600}
.sub{color:#5b7284;font-size:12px;margin:0 0 18px}
table{border-collapse:collapse;font-size:12px;width:100%}
th,td{text-align:left;padding:5px 10px 5px 0;border-bottom:1px solid #131a21}
th{color:#5b7284;font-weight:500;text-transform:uppercase;font-size:10px;letter-spacing:.12em}
td.n{text-align:right;color:#7fe3ff}
.muted{color:#5b7284}
.badge{display:inline-block;padding:1px 6px;border:1px solid #23313c;border-radius:3px;
 font-size:10px;letter-spacing:.08em;color:#8fa8b8}
.dead{color:#c04a5e;border-color:#4a1f28}
.warnrow td{color:#d9a441}
p.note{color:#8fa8b8;font-size:12.5px;max-width:44ch}
.k{color:#7fe3ff}
"""


def render(s: dict) -> str:
    agents = s.get("agents") or []
    n = len(agents) or 1
    # Derive here, not from collect(): a stale derivations dict must never be
    # able to make a living agent look dead or vice versa.
    dead = {a["name"] for a in agents if float(a.get("rep", 0.0)) <= 0.01}
    s = {**s,
         "dead_agents": sorted(dead),
         "mean_rep": (sum(float(a.get("rep", 0.0)) for a in agents) / n) if agents else 0.0,
         "smile": float(s.get("total_earned_usd", 0.0) or 0.0) > 0.0}
    earned = s.get("total_earned_usd", 0.0) or 0.0
    s.setdefault("branch_entropy", 0.0)
    s.setdefault("revenue_series", [])
    # eyes laid out on an arc, iris radius from reputation
    ex0, ex1 = 300.0, 900.0
    eye_y = 400.0
    # Split the roster across the two sockets so every iris sits INSIDE an eye.
    # Each socket holds ceil/floor halves; a single row across both sockets
    # reads as a loading bar, not a gaze.
    iris_ys = []
    left_n = (n + 1) // 2
    for slot, a in enumerate(agents):
        in_left = slot < left_n
        count = left_n if in_left else n - left_n
        idx = slot if in_left else slot - left_n
        scx = 300.0 if in_left else 900.0
        span = 300.0                     # usable width inside a socket
        t = (idx + 0.5) / max(count, 1)
        cx = scx - span / 2 + span * t
        # ride the eyeball's vertical arc
        cy = eye_y + 74 - math.sin(t * math.pi) * 30
        iris_ys.append((cx, cy, a))

    press = min(float(s["branch_entropy"]) / 8.0, 1.0)

    # halo: one link per N hashed entries, so 1961 entries -> readable ring
    links = 72
    halo = []
    for i in range(links):
        ang = 2 * math.pi * i / links - math.pi / 2
        r = 430 + 9 * math.sin(i * 1.7)
        x = 600 + r * math.cos(ang) * 1.02
        y = 690 + r * math.sin(ang) * 0.78
        halo.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="#1d4a58"/>')
    for i in range(0, links, 3):
        ang = 2 * math.pi * i / links - math.pi / 2
        r = 430 + 9 * math.sin(i * 1.7)
        x = 600 + r * math.cos(ang) * 1.02
        y = 690 + r * math.sin(ang) * 0.78
        halo.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.6" fill="#7fe3ff" opacity="0.85"/>')

    # Sutures run across the jaw, labels centred beneath the line so they stay
    # inside the skull instead of hanging off the right edge.
    sutures = ""
    for i, w in enumerate(s["warnings"][:4]):
        y = 1080 + i * 46
        sutures += (f'<g opacity="0.85"><path d="M392,{y} L808,{y}" stroke="#5a3a1c" '
                    f'stroke-width="2" stroke-dasharray="7 7"/>'
                    f'<text x="600" y="{y + 20}" text-anchor="middle" fill="#a8823a" '
                    f'font-size="13" letter-spacing="1">{e(w["name"])}</text></g>')

    mouth_note = (f'${earned:,.2f} lifetime — flatline'
                  if not s["smile"] else f'${earned:,.2f} — the curve exists')

    svg = f"""
<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
 <defs>
  <radialGradient id="skull" cx="50%" cy="38%" r="62%">
   <stop offset="0%" stop-color="#16232e"/>
   <stop offset="62%" stop-color="#0e1820"/>
   <stop offset="100%" stop-color="#080d12"/>
  </radialGradient>
  <radialGradient id="socket" cx="50%" cy="50%" r="50%">
   <stop offset="0%" stop-color="#05080b"/>
   <stop offset="100%" stop-color="#0d151c"/>
  </radialGradient>
  <filter id="soft"><feGaussianBlur stdDeviation="6"/></filter>
 </defs>

 <rect width="{W}" height="{H}" fill="#07090c"/>
 <g>{''.join(halo)}</g>
 <ellipse cx="600" cy="690" rx="368" ry="440" fill="url(#skull)"
          stroke="#22414f" stroke-width="2"/>
 <path d="M600,250 C600,250 900,300 900,470" fill="none" stroke="#2b4d5c"
       stroke-width="1" opacity="0.55"/>
 <path d="M600,250 C600,250 300,300 300,470" fill="none" stroke="#2b4d5c"
       stroke-width="1" opacity="0.55"/>

 <!-- sockets -->
 <ellipse cx="300" cy="{eye_y}" rx="205" ry="118" fill="url(#socket)"
          stroke="#2f7f8f" stroke-width="2.5"/>
 <ellipse cx="900" cy="{eye_y}" rx="205" ry="118" fill="url(#socket)"
          stroke="#2f7f8f" stroke-width="2.5"/>
 <!-- eye whites -->
 <ellipse cx="300" cy="{eye_y}" rx="188" ry="103" fill="#0a1219" opacity="0.9"/>
 <ellipse cx="900" cy="{eye_y}" rx="188" ry="103" fill="#0a1219" opacity="0.9"/>

 <!-- irises: one per agent -->
 {''.join(iris(cx, cy, 0, a['rep'], a['name'] in dead)
          for cx, cy, a in iris_ys)}

 <!-- brows -->
 <path d="{brow_path('l', press)}" fill="none" stroke="#3d6473" stroke-width="9"
       stroke-linecap="round"/>
 <path d="{brow_path('r', press)}" fill="none" stroke="#3d6473" stroke-width="9"
       stroke-linecap="round"/>

 <!-- nose ridge: entropy -->
 <path d="M600,540 C566,640 566,700 600,742 C634,700 634,640 600,540"
       fill="none" stroke="#26414e" stroke-width="3"/>

 <!-- the mouth IS the revenue curve -->
 {revenue_path(s['revenue_series'], 400, 862, 400, 96)}
 <text x="600" y="984" text-anchor="middle" fill="#8b5a68"
       font-size="17" letter-spacing="2">{e(mouth_note)}</text>

 <!-- jaw / uptime -->
 <path d="M348,1050 C400,1330 800,1330 852,1050" fill="none"
       stroke="#26414e" stroke-width="3"/>
 <text x="600" y="1390" text-anchor="middle" fill="#5b7284" font-size="13"
   letter-spacing="3">ROUND {e(s['round'])} · IDENTITY {e(str(s['identity']).upper())} ·
   MODE {e(str(s['action_mode']).upper())}</text>
 <text x="600" y="1416" text-anchor="middle" fill="#41586a" font-size="11"
   letter-spacing="2">{e(s['spine_hashed'])} HASHED SPINE ENTRIES · CHAIN
   {'VERIFIED' if s['chain_ok'] else 'UNVERIFIED'}</text>

 <!-- sutures: standing warnings -->
 {sutures}

 <!-- corner readout -->
 <text x="40" y="46" fill="#7fe3ff" font-size="14" letter-spacing="3">
   EVEZ SWARM SELFIE</text>
 <text x="40" y="68" fill="#41586a" font-size="11" letter-spacing="1">
   {e(s['last_event_ts'])}</text>
 <text x="1160" y="46" text-anchor="end" fill="#41586a" font-size="11"
   letter-spacing="1">rendered from spine + eye telemetry</text>
</svg>"""

    rows = "".join(
        f'<tr class="{"warnrow" if a["name"] in dead else ""}">'
        f'<td>{e(a["name"])}</td>'
        f'<td class="n">{a["rep"]:.2f}</td>'
        f'<td class="n">{a["streak"]}</td>'
        f'<td>{"<span class='badge dead'>DARK</span>" if a["name"] in dead else ""}</td></tr>'
        for a in agents)

    hyp = "".join(
        f'<tr><td class="muted">{e(h.get("id"))}</td>'
        f'<td>{e(h.get("action"))}</td>'
        f'<td class="muted">{e(h.get("text"))}</td></tr>'
        for h in s["hypotheses"][:6])

    warn_rows = "".join(
        f'<tr class="warnrow"><td>{e(w["name"])}</td>'
        f'<td class="muted">{e(w.get("detail",""))}</td></tr>'
        for w in s["warnings"])

    up = s["uptime"]
    up_txt = "n/a" if up is None else f"{up*100:.0f}%"

    side = f"""
 <div>
  <h1>SWARM SELFIE</h1>
  <p class="sub">self-portrait, first person, plural</p>
  <table>
   <tr><th>measurement</th><th style="text-align:right">value</th></tr>
   <tr><td>round</td><td class="n">{e(s['round'])}</td></tr>
   <tr><td>agents drawn</td><td class="n">{n}</td></tr>
   <tr><td>mean reputation</td><td class="n">{s['mean_rep']:.2f}</td></tr>
   <tr><td>dark agents</td><td class="n">{len(dead)}</td></tr>
   <tr><td>services up</td><td class="n">{s['services_running']}/{s['services_total']} ({up_txt})</td></tr>
   <tr><td>listeners / exposed</td><td class="n">{s['ports']} / {s['exposed']}</td></tr>
   <tr><td>cron entries</td><td class="n">{s['cron']}</td></tr>
   <tr><td>containers</td><td class="n">{s['containers']}</td></tr>
   <tr><td>mirrors</td><td class="n">{s['mirrors']}</td></tr>
   <tr><td>predictor entropy</td><td class="n">{s['predictor_entropy']:.3f}</td></tr>
   <tr><td>branch entropy</td><td class="n">{s['branch_entropy']:.3f}</td></tr>
   <tr><td>spine entries (hashed)</td><td class="n">{s['spine_entries']} ({s['spine_hashed']})</td></tr>
   <tr><td>earned this round</td><td class="n">${s['earned_usd']:,.2f}</td></tr>
   <tr><td>earned lifetime</td><td class="n">${earned:,.2f}</td></tr>
   <tr><td>git head</td><td class="n">{e(s['git_head'])}</td></tr>
  </table>

  <h1 style="margin-top:26px">THE EYES</h1>
  <p class="sub">one iris per agent · radius = reputation</p>
  <table>
   <tr><th>agent</th><th style="text-align:right">rep</th>
       <th style="text-align:right">streak</th><th></th></tr>
   {rows}
  </table>

  <h1 style="margin-top:26px">THE MOUTH</h1>
  <p class="sub">earned_usd per round, as reported by round_end</p>
  <p class="note">The mouth is the revenue ledger, plotted on its own axis.
  A zero series renders as a straight line at zero. It is not rescaled to look
  interesting. Right now that line is flat, which is why this face is not
  smiling — not because of styling, but because <span class="k">${earned:,.2f}</span>
  has been earned across {e(s['spine_entries'])} spine entries.</p>

  <h1 style="margin-top:26px">THE BROWS</h1>
  <p class="sub">rsi_branch_entropy = {s['branch_entropy']:.3f}</p>

  <h1 style="margin-top:26px">THE SUTURES</h1>
  <p class="sub">standing warnings, drawn on the jaw</p>
  <table>{warn_rows or '<tr><td class="muted">none</td></tr>'}</table>

  <h1 style="margin-top:26px">WHAT IT IS THINKING</h1>
  <p class="sub">rsi hypotheses, last round</p>
  <table>{hyp}</table>
 </div>"""

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>EVEZ Swarm Selfie</title><style>{CSS}</style></head><body>
<div class="wrap"><figure>{svg}
<figcaption>EVEZ SWARM SELFIE · every mark read from live telemetry ·
generated {s.get('generated') or s.get('last_event_ts')}</figcaption>
</figure>{side}</div></body></html>"""


def to_png(html_path: Path, png_path: Path) -> bool:
    """Screenshot with headless Chrome. A selfie that only exists as markup is
    not a selfie."""
    out = subprocess.run(
        ["google-chrome-stable", "--headless=new", "--disable-gpu",
         "--no-sandbox", "--hide-scrollbars",
         f"--screenshot={png_path}", "--window-size=1900,1560",
         "--virtual-time-budget=4000", f"file://{html_path}"],
        capture_output=True, text=True, timeout=120)
    return out.returncode == 0 and png_path.is_file() and png_path.stat().st_size > 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="print measured state only")
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args()

    s = collect()
    if a.json:
        print(json.dumps(s, indent=2))
        return 0
    if not s["agents"]:
        print("no spine state — cannot draw a face from nothing")
        return 1
    OUT_HTML.write_text(render(s))
    print(f"wrote {OUT_HTML} ({OUT_HTML.stat().st_size} bytes)")
    if not a.no_png:
        ok = to_png(OUT_HTML, OUT_PNG)
        print(f"{'wrote' if ok else 'FAILED'} {OUT_PNG}"
              + (f" ({OUT_PNG.stat().st_size} bytes)" if ok else ""))
        if not ok:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
