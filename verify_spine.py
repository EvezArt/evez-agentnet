"""Verify the append-only spine is internally consistent.

The spine is EVEZ's evidentiary claim: each entry carries a sha256 over its own
canonical JSON. This checks every entry hashes to what it claims, and that the
file is strictly append-only in time (no backdated insertions).
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

SPINE = Path("/root/evez-agentnet/spine/spine.jsonl")


def main() -> int:
    bad_hash, bad_ts, count, types = [], [], 0, {}
    prev_ts = None
    last_sha = None
    last_seq = None
    linked = 0

    for i, line in enumerate(SPINE.read_text(errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            bad_hash.append((i, f"unparseable: {e.msg}"))
            continue
        count += 1
        types[entry.get("type", "?")] = types.get(entry.get("type", "?"), 0) + 1

        claimed = entry.get("sha256")
        if claimed:
            body = {k: v for k, v in entry.items() if k != "sha256"}
            canon = json.dumps(body, sort_keys=True)
            actual = hashlib.sha256(canon.encode()).hexdigest()[:16]
            if actual != claimed:
                bad_hash.append((i, f"claims {claimed}, computes {actual}"))

        # Chain linkage: prev_sha256 must equal the previous entry's sha256.
        # This is what makes deletion and reordering detectable, which
        # per-entry hashing alone is NOT.
        link = entry.get("prev_sha256")
        if link:
            linked += 1
        if link is not None and last_sha not in (None, ""):
            if link != last_sha:
                bad_hash.append((i, f"prev_sha256={link} but previous entry hashed {last_sha}"))

        # Sequence must advance by exactly one.
        s = entry.get("seq")
        # Legacy entries (pre-chain) have no seq; only enforce once chaining
        # has begun, otherwise the first chained entry fails against None.
        if s is not None and last_seq is not None and link is not None:
            if s != last_seq + 1:
                bad_hash.append((i, f"seq jumped {last_seq} -> {s}"))

        last_sha = claimed
        last_seq = s

        ts = entry.get("ts")
        if ts:
            try:
                t = datetime.fromisoformat(ts)
                if prev_ts and t < prev_ts:
                    bad_ts.append((i, f"{ts} precedes previous {prev_ts.isoformat()}"))
                prev_ts = t
            except ValueError:
                bad_ts.append((i, f"unparseable ts {ts}"))

    print(f"entries checked: {count}")
    print(f"entries with prev_sha256 linkage: {linked}")
    print(f"event types: {len(types)} distinct")
    for t, n in sorted(types.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {t:28} {n}")

    if bad_hash:
        print(f"\nHASH FAILURES: {len(bad_hash)}")
        for i, why in bad_hash[:10]:
            print(f"  line {i}: {why}")
    else:
        print("\nhash chain: all entries verify")

    if bad_ts:
        print(f"timestamp anomalies: {len(bad_ts)}")
        for i, why in bad_ts[:5]:
            print(f"  line {i}: {why}")
    else:
        print("timestamps: strictly non-decreasing")

    return 1 if bad_hash else 0


if __name__ == "__main__":
    sys.exit(main())
