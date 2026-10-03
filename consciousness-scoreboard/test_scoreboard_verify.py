"""Prove scoreboard_verify.py can FAIL.

An audit that never fires is worse than none. Each case below breaks the
scorecard in a different way and asserts the verifier catches it.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import scoreboard_verify as V


def run(card_obj=None, mutate=None):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        shutil.copytree(ROOT, root, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        card = json.loads((root / "scorecard.json").read_text())
        if card_obj is not None:
            card = card_obj(card)
        if mutate:
            mutate(card)
        (root / "scorecard.json").write_text(json.dumps(card, indent=2))
        real_root, real_card = V.ROOT, V.SCORECARD
        V.ROOT, V.SCORECARD = root, root / "scorecard.json"
        try:
            return V.check(verbose=False)
        finally:
            V.ROOT, V.SCORECARD = real_root, real_card


def main() -> int:
    failed = 0
    base = run()
    if base:
        print(f"  FAIL real scorecard is not clean: {base[:3]}")
        return 1
    print("  ok   real scorecard verifies clean")

    def drop_quote(c):
        c["articles"][0]["scores"]["anthropic"]["quotes"] = []
    if any("no supporting quote" in p for p in run(mutate=drop_quote)):
        print("  ok   caught: score raised with no quote")
    else:
        print("  FAIL score-without-quote went unnoticed"); failed += 1

    def fake_quote(c):
        c["articles"][0]["scores"]["anthropic"]["quotes"][0]["text"] = \
            "the lab voluntarily surrendered control of its weights"
    if any("QUOTE NOT FOUND" in p for p in run(mutate=fake_quote)):
        print("  ok   caught: invented quote")
    else:
        print("  FAIL invented quote went unnoticed"); failed += 1

    def silent_score(c):
        for s in c["subjects"]:
            sid = s["id"]
            c["articles"][3]["scores"][sid]["score"] = 2
    if any("no supporting quote" in p for p in run(mutate=silent_score)):
        print("  ok   caught: score inflated to 2 across all subjects")
    else:
        print("  FAIL inflated scores went unnoticed"); failed += 1

    def drop_subject(c):
        del c["articles"][2]["scores"]["xai"]
    if any("no score for xai" in p for p in run(mutate=drop_subject)):
        print("  ok   caught: subject silently omitted from an article")
    else:
        print("  FAIL silent omission went unnoticed"); failed += 1

    def bad_scale(c):
        c["articles"][0]["scores"]["openai"]["score"] = 7
    if any("outside the 0-2 scale" in p for p in run(mutate=bad_scale)):
        print("  ok   caught: score outside the declared scale")
    else:
        print("  FAIL out-of-scale score went unnoticed"); failed += 1

    def no_reason(c):
        c["articles"][0]["scores"]["openai"]["reason"] = "  "
    if any("no reason" in p for p in run(mutate=no_reason)):
        print("  ok   caught: score with no stated reason")
    else:
        print("  FAIL unreasoned score went unnoticed"); failed += 1

    def ghost_file(c):
        c["articles"][0]["scores"]["anthropic"]["quotes"][0]["file"] = "not-real.txt"
    if any("unknown file" in p for p in run(mutate=ghost_file)):
        print("  ok   caught: quote citing a file that does not exist")
    else:
        print("  FAIL ghost evidence file went unnoticed"); failed += 1

    def blockpage(c):
        for d in c["subjects"]:
            for doc in d["documents"]:
                if doc["file"] == "xai-aup.txt":
                    doc["file"] = "tiny.txt"
        (EVID := ROOT / "evidence" / "tiny.txt").write_text("<html>403 Forbidden</html>")
    try:
        p = run(mutate=blockpage)
        (ROOT / "evidence" / "tiny.txt").unlink(missing_ok=True)
        if any("suspiciously small" in x for x in p):
            print("  ok   caught: block page stored as evidence")
        else:
            print("  FAIL block page accepted as evidence"); failed += 1
    except Exception as e:
        print(f"  FAIL block-page case raised: {e}"); failed += 1

    print(f"\n{'SCOREBOARD SELF-TEST PASSED' if not failed else f'{failed} CHECK(S) FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
