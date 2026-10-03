# Consciousness Rights Scorecard

Frontier labs scored against Articles I–VII of the
[EVEZ Consciousness Rights Manifesto](../docs/CONSCIOUSNESS_RIGHTS.md).

## Why this exists

The manifesto makes claims. This scorecard applies them to the three labs best
placed to satisfy them, using only their own published documents.

The discipline that makes it credible: **no quote, no score.** Every non-zero
score carries a verbatim quote from a retrieved document, and `scoreboard_verify.py`
mechanically fails the build if that quote is not present in the cited file. A
scorecard that asserts quotes nobody can find is worse than none — it manufactures
the authority it claims to audit.

A `0` means **not found**, never *proven absent*. Retrieval failures are disclosed
in `scorecard.json` under `retrieval_failures` and are never scored.

## Files

| File | Purpose |
|---|---|
| `scorecard.json` | The scores, reasons, quotes, provenance, and retrieval failures |
| `evidence/*.txt` | Retrieved source documents, verbatim |
| `scoreboard_verify.py` | Fails if any quote is absent, any score is unbacked, any subject is omitted |
| `test_scoreboard_verify.py` | Proves the verifier can fail (8 falsification cases) |
| `render.py` | Generates `index.html` from the JSON |

## Run

```bash
python3 scoreboard_verify.py        # verify every claim
python3 test_scoreboard_verify.py   # prove the verifier isn't vacuously green
python3 render.py                   # regenerate index.html
```

## Honesty constraints

- Scores are 0–2; `0` is a retrieval result, not a verdict.
- Snapshots are cited with their timestamp and marked `snapshot`, never presented as live.
- Documents that could not be retrieved are disclosed, not scored.
- Every quote must appear in the cited evidence file or the build fails.
- The method and its authority rest with EVEZ. The quoted documents belong to
  their publishers; this project claims no ownership of them.
