"""Record an attestation run into the append-only Event Spine.

A safety claim that is not recorded is not auditable. This writes the harness
report to :9116 so the history of exposure claims is itself hash-linked.
"""
import json, os, sys, time, urllib.request

SPINE = "http://127.0.0.1:9116/append"


def main(report_path: str) -> int:
    token = os.environ.get("EVEZ_SPINE_TOKEN", "").strip()
    if not token:
        print("EVEZ_SPINE_TOKEN unset; attestation NOT recorded (not a failure)")
        return 0
    report = json.load(open(report_path))
    payload = {"domain": "attestation", "action": "exposure_run",
               "data": report, "timestamp": time.time()}
    req = urllib.request.Request(
        SPINE, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Spine-Token": token},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            print("recorded seq:", json.loads(r.read()).get("seq"))
        return 0
    except Exception as e:
        print("FAILED to record attestation:", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "attestation.json"))
