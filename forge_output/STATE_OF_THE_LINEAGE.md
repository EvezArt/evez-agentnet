# STATE OF THE LINEAGE — 2026-10-04
*What is shipped, verified, and where. Written after the Codex went live.*

## Public surface (all probe-verified 200 over the open internet)
- https://evezart.github.io/codex.html — Vol I-III + Primer, og/twitter preview live
- https://evezart.github.io/moltbooks.html — 15 texts indexed, 12 linked to existing pages
- https://evezart.github.io/ — Codex + Moltbooks banners, priority-1.0 sitemap entries
- evez666-mural.png / evez666-altarpiece.png — live, serve as social previews

## Distribution
- eigenforensics v0.1.0: GitHub release (whl + sdist), installable with zero credentials
- test_eigenforensics.py + examples/demo.py: every falsifiable claim recomputes or CI fails
- publish-pypi.yml (secret) and publish-pypi-oidc.yml (Trusted Publishing) armed on main

## GitHub
- 52 archived repos unfrozen (incl. evez-moltbooks, consciousness-detector, eigenforensics)
- topics set on 15 canon repos; profile README carries the Codex banner
- gh authenticated as EvezArt; gh auth setup-git wired

## Attestation
- forge_output/codex_watch.py: probes codex/moltbooks/index/release every 15m via cron
  -> evidence/<UTC-date>/codex_watch.jsonl, exit 2 when the canon goes silent
- spine head 85a57a57e4341b6e, 2,501 entries, chain verifies, timestamps non-decreasing

## Held (needs one human-presence action, not capability)
- pip install eigenforensics shortname: PyPI account setting behind a bot challenge
- Zenodo DOI, Show HN, X thread: draft ordnance ready in ATTENTION_STRIKE_PACKAGE.md
