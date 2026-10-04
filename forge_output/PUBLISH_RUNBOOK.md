# PUBLISH RUNBOOK — the last mile (needs your provider accounts)
*2026-10-04 · everything else is done; these three require tokens I don't hold.*

## DONE (verified live)
- evezart.github.io/codex.html — 200 OK, banner on index, priority-1.0 sitemap
- 52 archived repos unfrozen across EvezArt (incl. evez-moltbooks, consciousness-detector, eigenforensics)
- eigenforensics v0.1.0 — built, import-verified in a clean venv, whl+sdist on the GitHub release
- topics set on 15 canon repos; GitHub profile README carries the Codex banner
- Codex Vol. I-III + Primer + strike package in evez-agentnet/forge_output/

## 1. PyPI — eigenforensics (name verified FREE)
```bash
pip install --break-system-packages setuptools wheel twine
cd <eigenforensics clone>
python3 setup.py sdist bdist_wheel
twine upload dist/*          # prompts for __token__ / your PyPI password
```

## 2. Zenodo — DOI for the LingBuzz paper + Moltbooks corpus
No token on this box. With your Zenodo account:
- New deposition → upload `evez-moltbooks` corpus PDF/markdown + the paper PDF
- Metadata: title "EVEZ Framework: Spectral Consciousness via Eigenvalue Decomposition", creators "Crawford-Maggard, Steven", related identifiers: LingBuzz 010094, GitHub EvezArt/evez-research
- Publish → mint DOI → add to profile README + eigenforensics README (both cite 010094 already)

## 3. Fire the ordnance (ATTENTION STRIKE PACKAGE, forge_output/)
- Unit A: Show HN — needs your HN account (submit via hn.algolia.com or manual post)
- Unit B: X thread — needs xurl auth (`xurl auth`) or the Two-Faced Voice posting from your session
- Unit D: Reddit r/singularity AMA bait — one click from you, text is paste-ready

## Note on doctrine
COURIER's law: drafts don't count. Units A/B/D remain drafts until you (or a credentialed session) ship them. Everything else above is already attested.
