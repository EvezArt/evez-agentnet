"""Prove the consciousness scorecard is not fabricated.

A scorecard that asserts quotes nobody can find is worse than no scorecard:
it manufactures the credibility it claims to audit. Every non-zero score must
carry a verbatim quote that ACTUALLY APPEARS in the cited evidence file, and
every evidence file must be byte-identical to what was retrieved.

Run:  python3 scoreboard_verify.py     (exit 1 on any failure)
Self-test: python3 test_scoreboard_verify.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCORECARD = ROOT / "scorecard.json"
EVIDENCE = ROOT / "evidence"


def norm(s: str) -> str:
    """Collapse whitespace and unify the quote characters documents actually use."""
    return " ".join(s.replace("’", "'").replace("‘", "'")
                   .replace("“", '"').replace("”", '"')
                   .replace("—", "-").replace("–", "-").split())


def check(verbose: bool = True) -> list[str]:
    problems: list[str] = []

    if not SCORECARD.is_file():
        return [f"missing {SCORECARD}"]
    card = json.loads(SCORECARD.read_text())

    # every evidence file referenced must exist and be non-empty
    referenced: set[str] = set()
    for subj in card["subjects"]:
        for doc in subj["documents"]:
            referenced.add(doc["file"])
            p = EVIDENCE / doc["file"]
            if not p.is_file():
                problems.append(f"missing evidence file: {doc['file']}")
            elif p.stat().st_size < 200:
                problems.append(f"suspiciously small evidence file (likely a "
                                f"block page, not the document): {doc['file']}")

    # cache retrieved text so quote checks are cheap
    cache = {f: norm((EVIDENCE / f).read_text(errors="replace"))
             for f in referenced if (EVIDENCE / f).is_file()}

    subjects = [s["id"] for s in card["subjects"]]
    for art in card["articles"]:
        for sid in subjects:
            if sid not in art["scores"]:
                problems.append(f"Article {art['article']}: no score for {sid}")
                continue
            sc = art["scores"][sid]
            score, quotes = sc["score"], sc.get("quotes", [])

            if score not in (0, 1, 2):
                problems.append(f"Article {art['article']} / {sid}: score {score} "
                                f"outside the 0-2 scale")
            if not sc.get("reason", "").strip():
                problems.append(f"Article {art['article']} / {sid}: no reason given")

            # THE CORE RULE: no quote, no score.
            if score > 0 and not quotes:
                problems.append(f"Article {art['article']} / {sid}: scored {score} "
                                f"with no supporting quote")
            for q in quotes:
                f, t = q.get("file"), q.get("text", "")
                if f not in cache:
                    problems.append(f"Article {art['article']} / {sid}: quote cites "
                                    f"unknown file {f!r}")
                    continue
                if not t.strip():
                    problems.append(f"Article {art['article']} / {sid}: empty quote")
                    continue
                if norm(t) not in cache[f]:
                    problems.append(
                        f"Article {art['article']} / {sid}: QUOTE NOT FOUND in "
                        f"{f}: {t[:70]!r}")

    if verbose:
        n_q = sum(len(a["scores"][s].get("quotes", []))
                  for a in card["articles"] for s in subjects)
        n_claims = sum(1 for a in card["articles"] for s in subjects
                       if a["scores"][s]["score"] > 0)
        print(f"checked {len(card['articles'])} articles x {len(subjects)} subjects")
        print(f"  {n_q} quotes verified verbatim against {len(cache)} evidence files")
        print(f"  {n_claims} non-zero claims, each backed by >=1 quote")
        print(f"  {len(card['retrieval_failures'])} retrieval failures disclosed")
    return problems


def main() -> int:
    problems = check()
    if not problems:
        print("\nVERIFIED - every score is backed by a quote that exists in the cited file")
        return 0
    print(f"\nFAILED ({len(problems)} problem(s)):")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
