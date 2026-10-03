"""EVEZ EYE — render the operational picture to a single self-contained page.

No build step, no CDN, no framework. One file that opens anywhere and works
offline, because an operator should not need a network to see their own state.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.json"


def e(x) -> str:
    return html.escape(str(x))


def render(d: dict) -> str:
    exposed = [p for p in d["ports"] if p["exposed"]]
    blocked = [p for p in d["ports"] if p["fw_blocked"]]
    tail = [p for p in d["ports"] if p["tailnet"]]
    local = [p for p in d["ports"] if not p["public_bind"] and not p["tailnet"]]
    warns = [c for c in d["checks"] if c["state"] == "WARN"]
    creds = d["credentials"]
    cred_live = sum(c["count"] for c in creds)

    # ── headline numbers ──
    tiles = [
        ("SERVICES", len(d["services"]), "acc"),
        ("EXPOSED", len(exposed), "bad" if exposed else "acc"),
        ("PORTS", len(d["ports"]), ""),
        ("CRON", len(d["cron"]), ""),
        ("MIRRORS", d["mirrors"], ""),
        ("WARN", len(warns), "warn" if warns else "acc"),
        ("LIVE CREDS", cred_live, "bad" if cred_live else "acc"),
    ]
    tile_html = "".join(
        f'<div class="tile {c}"><div class="n">{v}</div>'
        f'<div class="l">{l}</div></div>' for l, v, c in tiles)

    # ── services ──
    svc = "".join(
        f'<tr><td class="mono">{e(s["unit"])}</td>'
        f'<td><span class="dot ok"></span>{e(s["sub"] or "running")}</td>'
        f'<td class="dim mono">{e(s["since"])}</td></tr>'
        for s in d["services"])

    # ── attack surface: the honest taxonomy ──
    def prow(p, cls, note):
        return (f'<tr><td class="mono">:{p["port"]}</td>'
                f'<td class="mono">{e(p["bind"])}</td>'
                f'<td>{e(p["proc"])}</td>'
                f'<td><span class="tag {cls}">{cls.upper()}</span> {e(note)}</td></tr>')

    surf = (prow_rows(exposed, "bad", "internet-reachable")
            + prow_rows(blocked, "guard", "public bind, firewalled")
            + prow_rows(tail, "ok", "tailnet only")
            + prow_rows(local, "ok", "loopback only"))

    # ── checks ──
    chk = "".join(
        f'<div class="chk {c["state"].lower()}"><div class="ch">'
        f'<span class="tag {"bad" if c["state"]=="WARN" else "ok"}">{c["state"]}</span>'
        f'{e(c["name"])}</div><div class="cd">{e(c["detail"])}</div></div>'
        for c in d["checks"]) or '<p class="dim">no checks reported</p>'

    # ── cron ──
    cron = "".join(f'<tr><td class="mono dim">{e(c["sched"])}</td>'
                   f'<td class="mono">{e(c["cmd"])}</td></tr>' for c in d["cron"])

    # ── docker ──
    dock = "".join(f'<tr><td class="mono">{e(x["name"])}</td>'
                   f'<td class="dim">{e(x["status"])}</td>'
                   f'<td class="mono dim">{e(x["image"])}</td></tr>'
                   for x in d["docker"])

    # ── credentials ──
    cred = "".join(
        f'<tr><td>{e(c["name"])} <span class="mono dim">{e(c["prefix"])}…</span></td>'
        f'<td>{"<span class=\'tag bad\'>LIVE</span>" if c["count"] else "<span class=\'tag ok\'>CLEAN</span>"}'
        f' <span class="dim">{c["count"]} literal(s) in working tree</span></td></tr>'
        for c in creds)

    g = d["git"]
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EVEZ EYE — {e(d["operator"])}</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ccircle cx='8' cy='8' r='6' fill='%2300ff9c'/%3E%3C/svg%3E">
<style>
:root{{--bg:#08090b;--fg:#e9ecef;--dim:#767b83;--line:#1e2126;--acc:#00ff9c;
--bad:#ff4d4f;--warn:#ffb454;--ok:#3ddc84;--guard:#4fd6ff}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font:14px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;margin:0;padding:2rem 1.25rem}}
.wrap{{max-width:1400px;margin:0 auto;overflow-x:hidden}}
header{{border-bottom:1px solid var(--line);padding-bottom:1rem;margin-bottom:1.5rem}}
h1{{margin:0;font-size:1.4rem;letter-spacing:-.02em}}
h1 span{{color:var(--acc)}}
.sub{{color:var(--dim);font-size:.8rem;margin-top:.35rem}}
.live{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--acc);
margin-right:.4rem;animation:p 2s infinite}}
@keyframes p{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:.7rem;margin-bottom:2rem}}
.tile{{border:1px solid var(--line);padding:.9rem;background:#0e1013}}
.tile .n{{font-size:2rem;line-height:1}}
.tile .l{{color:var(--dim);font-size:.68rem;letter-spacing:.1em;margin-top:.35rem}}
.tile.acc .n{{color:var(--acc)}}.tile.bad .n{{color:var(--bad)}}.tile.warn .n{{color:var(--warn)}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.4rem}}
@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}
section{{border:1px solid var(--line);padding:1rem 1.1rem;background:#0b0d10}}
section h2{{margin:0 0 .8rem;font-size:.82rem;letter-spacing:.12em;color:var(--acc);
text-transform:uppercase;border-bottom:1px solid var(--line);padding-bottom:.5rem}}
table{{width:100%;border-collapse:collapse;font-size:.8rem;table-layout:auto}}
table.tight td:nth-child(1){{width:4.5rem;white-space:nowrap}}
table.tight td:nth-child(2){{width:7.2rem;white-space:nowrap}}
table.tight td:nth-child(3){{width:5.5rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
table.tight td:nth-child(4){{white-space:nowrap;font-size:.72rem}}
td,th{{padding:.34rem .4rem;border-bottom:1px solid #16181c;text-align:left;vertical-align:top}}
td.mono,.mono{{font-family:inherit}}
.dim{{color:var(--dim)}}
.tag{{display:inline-block;padding:0 .35rem;font-size:.65rem;border:1px solid currentColor;margin-right:.3rem}}
.tag.ok{{color:var(--ok)}}.tag.bad{{color:var(--bad)}}.tag.warn{{color:var(--warn)}}.tag.guard{{color:var(--guard)}}
.dot{{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--ok);margin-right:.4rem}}
.chk{{border-left:2px solid var(--line);padding:.45rem .7rem;margin-bottom:.5rem}}
.chk.warn{{border-left-color:var(--warn)}}.chk.ok{{border-left-color:var(--ok)}}
.ch{{font-size:.82rem}}.cd{{color:var(--dim);font-size:.75rem;margin-top:.15rem}}
.note{{color:var(--dim);font-size:.76rem;border-left:2px solid var(--guard);
padding-left:.7rem;margin:.7rem 0}}
footer{{margin-top:2rem;border-top:1px solid var(--line);padding-top:.9rem;color:var(--dim);font-size:.75rem}}
a{{color:var(--guard)}}
</style></head><body><div class="wrap">
<header>
<h1><span>◉</span>EVEZ EYE</h1>
<div class="sub"><span class="live"></span>operator {e(d["operator"])} ·
system {e(d["system"])} · collected {e(d["generated"])} ·
{e(g["branch"])}@{e(g["head"])} · {g["dirty"]} uncommitted</div>
</header>

<div class="tiles">{tile_html}</div>

<div class="grid">
<section><h2>Services ({len(d["services"])})</h2>
<table>{svc}</table></section>

<section style="grid-column:1/-1"><h2>Attack surface ({len(d["ports"])} listening)</h2>
<p class="note">A port bound to <b>0.0.0.0</b> is not the same as a port reachable
from the internet. ufw INPUT policy is DROP, so a public bind with no ACCEPT rule
is firewalled. Only <b>EXPOSED</b> is an actual finding.</p>
<table class="tight">{surf}</table></section>

<section><h2>Health checks</h2>{chk}</section>

<section><h2>Credentials</h2>
<p class="note">Scanned for full-length literals, excluding synthetic test
fixtures. A bare prefix grep reports false positives here — this repo's own
detector code and its test fixtures both contain the literal prefix.</p>
<table>{cred}</table></section>

<section><h2>Cron ({len(d["cron"])})</h2>
<table>{cron}</table></section>

<section><h2>Containers ({len(d["docker"])})</h2>
<table>{dock}</table></section>
</div>

<footer>Every number above is probed at collection time by
<code>collect.py</code> — none are asserted or cached. Regenerate with
<code>python3 collect.py && python3 render.py</code>.
Last commit: {e(g["last"])}</footer>
</div></body></html>"""


def prow_rows(rows, cls, note):
    return "".join(
        f'<tr><td class="mono">:{p["port"]}</td>'
        f'<td class="mono">{e(p["bind"])}</td>'
        f'<td>{e(p["proc"])}</td>'
        f'<td><span class="tag {cls}">{cls.upper()}</span> {e(note)}</td></tr>'
        for p in rows)


if __name__ == "__main__":
    out = ROOT / "index.html"
    out.write_text(render(json.loads(DATA.read_text())))
    print(f"wrote {out} ({out.stat().st_size} bytes)")
