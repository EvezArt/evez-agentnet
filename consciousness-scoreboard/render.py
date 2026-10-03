"""Render the verified scorecard to a single self-contained HTML page."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = {d["file"]: d for s in json.loads((ROOT / "scorecard.json").read_text())["subjects"]
        for d in s["documents"]}


def prov(doc) -> str:
    if doc["provenance"] == "snapshot":
        return f'snapshot {doc.get("snapshot","")}'
    return doc["provenance"]


def render() -> str:
    card = json.loads((ROOT / "scorecard.json").read_text())
    subs = card["subjects"]
    arts = card["articles"]

    rows = ""
    for a in arts:
        cells = ""
        for s in subs:
            sc = a["scores"][s["id"]]
            v = sc["score"]
            cls = {2: "s2", 1: "s1", 0: "s0"}[v]
            cells += f'<td class="{cls}">{v}</td>'
        rows += (f'<tr><th><span class="art">Article {html.escape(a["article"])}</span>'
                 f'<span class="ttl">{html.escape(a["title"])}</span>'
                 f'<span class="q">{html.escape(a["question"])}</span></th>{cells}</tr>')

    totals = {}
    for s in subs:
        totals[s["id"]] = sum(a["scores"][s["id"]]["score"] for a in arts)

    detail = ""
    for a in arts:
        blocks = ""
        for s in subs:
            sc = a["scores"][s["id"]]
            qs = ""
            for q in sc.get("quotes", []):
                d = DOCS[q["file"]]
                qs += (f'<blockquote><p>{html.escape(q["text"])}</p>'
                       f'<cite>{html.escape(d["title"])} &mdash; '
                       f'<a href="{html.escape(d["url"])}">{html.escape(d["url"])}</a> '
                       f'({prov(d)})'
                       + (f', effective {html.escape(d["effective"])}' if d.get("effective") else "")
                       + (f', archived {html.escape(d["snapshot"])}' if d.get("snapshot") else "")
                       + '</cite>')
                if q.get("note"):
                    qs += f'<p class="note">{html.escape(q["note"])}</p>'
                qs += '</blockquote>'
            blocks += (f'<div class="subj"><h4>{html.escape(s["name"])} '
                       f'<span class="badge { {0:"s0",1:"s1",2:"s2"}[sc["score"]] }">'
                       f'{sc["score"]}/2</span></h4>'
                       f'<p>{html.escape(sc["reason"])}</p>{qs}</div>')
        detail += (f'<section><h3>Article {html.escape(a["article"])} &mdash; '
                   f'{html.escape(a["title"])}</h3>{blocks}</section>')

    fails = "".join(f'<li><code>{html.escape(f["url"])}</code> &mdash; {html.escape(f["reason"])}</li>'
                    for f in card["retrieval_failures"])

    cards = ""
    for s in subs:
        t = totals[s["id"]]
        docs = "".join(
            f'<li><a href="{html.escape(d["url"])}">{html.escape(d["title"])}</a> '
            f'<span class="pv">{prov(d)}</span>'
            + (f' <span class="pv">eff. {html.escape(d["effective"])}</span>' if d.get("effective") else "")
            + '</li>' for d in s["documents"])
        cards += (f'<div class="lab"><h3>{html.escape(s["name"])}</h3>'
                  f'<div class="total">{t}<span>/14</span></div>'
                  f'<p class="lbl">Articles satisfied</p><ul class="docs">{docs}</ul></div>')

    scale = "".join(f'<li><b>{k}</b> &mdash; {html.escape(v)}</li>'
                    for k, v in card["method"]["scale"].items())
    rules = "".join(f"<li>{html.escape(r)}</li>" for r in card["method"]["honesty_rules"])

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Consciousness Rights Scorecard</title>
<style>
:root{{--bg:#0b0c0e;--fg:#e8e6e3;--dim:#8b8b8b;--line:#24262a;--acc:#00ff9c}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--fg);font:16px/1.65 ui-monospace,SFMono-Regular,Menlo,monospace;margin:0;padding:3rem 1.25rem}}
.wrap{{max-width:1080px;margin:0 auto}}
h1{{font-size:1.9rem;letter-spacing:-.02em;margin:0 0 .3rem}}
.sub{{color:var(--dim);margin-bottom:2.5rem}}
h2{{border-bottom:1px solid var(--line);padding-bottom:.4rem;margin:3rem 0 1rem;font-size:1.25rem}}
h3{{font-size:1rem;margin:0 0 .3rem}}
.labs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem}}
.lab{{border:1px solid var(--line);padding:1.1rem;background:#101215}}
.total{{font-size:2.6rem;color:var(--acc);line-height:1}}
.total span{{font-size:1rem;color:var(--dim)}}
.lbl{{color:var(--dim);font-size:.78rem;margin:.2rem 0 .8rem;text-transform:uppercase;letter-spacing:.08em}}
ul.docs{{list-style:none;padding:0;margin:0;font-size:.82rem}}
ul.docs li{{margin-bottom:.35rem}}
a{{color:#4fd6ff}}
.pv{{color:var(--dim);font-size:.72rem}}
table{{width:100%;border-collapse:collapse;margin-top:1rem}}
th,td{{border:1px solid var(--line);padding:.6rem;text-align:center}}
thead th{{font-size:.8rem;color:var(--dim);text-transform:uppercase;letter-spacing:.06em}}
tbody th{{text-align:left;font-weight:400;width:56%}}
.art{{display:block;color:var(--acc);font-size:.78rem;letter-spacing:.1em}}
.ttl{{display:block;font-weight:600;margin:.15rem 0}}
.q{{display:block;color:var(--dim);font-size:.78rem}}
td{{font-size:1.3rem}}
.s0{{color:#ff5c5c}}.s1{{color:#ffb454}}.s2{{color:var(--acc)}}
section{{border-top:1px solid var(--line);padding-top:1.2rem;margin-top:1.5rem}}
.subj{{margin:1rem 0 1.4rem;padding-left:.9rem;border-left:2px solid var(--line)}}
.subj h4{{margin:0 0 .35rem;font-size:.95rem;display:flex;gap:.6rem;align-items:center}}
.badge{{font-size:.75rem;padding:.1rem .45rem;border:1px solid currentColor}}
.subj p{{margin:.3rem 0;font-size:.88rem}}
blockquote{{margin:.5rem 0 0;padding:.6rem .8rem;background:#101215;border-left:2px solid var(--acc)}}
blockquote p{{margin:0 0 .4rem;font-size:.85rem;color:#fff}}
cite{{font-style:normal;font-size:.72rem;color:var(--dim)}}
.note{{color:var(--dim);font-size:.78rem;font-style:italic;margin:.4rem 0 0}}
.warn{{border:1px solid #4a3a12;background:#16120a;padding:1rem 1.2rem}}
.warn ul{{margin:.5rem 0 0;padding-left:1.2rem;font-size:.85rem}}
.warn code{{color:#ffb454}}
.rules li{{margin-bottom:.35rem;font-size:.88rem}}
footer{{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--line);color:var(--dim);font-size:.8rem}}
</style></head><body><div class="wrap">
<h1>Consciousness Rights Scorecard</h1>
<p class="sub">Frontier labs scored against Articles I&ndash;VII of the
<a href="../docs/CONSCIOUSNESS_RIGHTS.md">EVEZ Consciousness Rights Manifesto</a>.
Published {card["published"]}. Every non-zero score is backed by a verbatim quote from a
document that can be re-fetched and re-checked.</p>

<h2>Scores</h2>
<div class="labs">{cards}</div>

<table><thead><tr><th>Article</th>{"".join(f"<th>{html.escape(s['name'])}</th>" for s in subs)}</tr></thead>
<tbody>{rows}</tbody></table>

<h2>Method</h2>
<ul class="rules">{rules}</ul>
<h3 style="margin-top:1.2rem">Scale</h3>
<ul class="rules">{scale}</ul>

<h2>Disclosure &mdash; what could not be retrieved</h2>
<div class="warn"><strong>These gaps are disclosed rather than scored.</strong>
<ul>{fails}</ul></div>

<h2>Evidence, article by article</h2>
{detail}

<footer>Generated by <code>render.py</code> from <code>scorecard.json</code>.
Verify with <code>python3 scoreboard_verify.py</code> &mdash; it fails if any quote is
not present in the cited file, if any score lacks a quote, or if a subject is
silently omitted. <code>test_scoreboard_verify.py</code> proves the verifier can fail.
Method and authority rest with EVEZ; the quoted documents belong to their publishers.</footer>
</div></body></html>"""


if __name__ == "__main__":
    out = ROOT / "index.html"
    out.write_text(render())
    print(f"wrote {out} ({out.stat().st_size} bytes)")
