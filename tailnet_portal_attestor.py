#!/usr/bin/env python3
"""Tailnet portal uptime attestor.

Proves, on an interval, that https://<tailnet-host>/ answers with a valid
cert and a healthy gateway. Appends one JSON line per probe to the dated
evidence file and exits non-zero when the portal is silent, so cron rows
surface in the watchdog evidence stream instead of rotting unnoticed.

Notes the one known-false-negative: a probe run ON the server itself is
403-attributed by the gateway (self-IP is a trusted proxy that strips to
nothing). The attestor therefore treats 403 with type=proxy_attribution_required
as PROOF the TLS+serve+proxy+gateway chain is alive end-to-end — the 403 is
produced by the gateway itself, which is the last hop. Any other failure
(refused, timeout, cert error, 5xx) is a real outage.
"""
from __future__ import annotations

import datetime as dt
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

HOST = "vmi3544756.tail613e80.ts.net"
URL = f"https://{HOST}/health"
EVIDENCE_ROOT = Path("/root/evez-agentnet/evidence")
ATTRIBUTION_403 = "proxy_attribution_required"


def utc_date() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def probe() -> dict:
    ctx = ssl.create_default_context()
    record: dict = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(), "check": "tailnet_portal"}
    try:
        with urllib.request.urlopen(URL, timeout=10, context=ctx) as resp:
            body = resp.read(256).decode(errors="replace")
            record.update(ok=True, http=resp.status, body=body[:120], cert_valid=True)
    except urllib.error.HTTPError as e:
        body = e.read(400).decode(errors="replace")
        # 403 proxy_attribution_required == gateway answered: the whole
        # chain is up; only the client-IP attribution policy refused US.
        chain_alive = e.code == 403 and ATTRIBUTION_403 in body
        record.update(ok=chain_alive, http=e.code,
                      reason="gateway_attribution_selftest" if chain_alive else "http_error",
                      body=body[:200], cert_valid=True)
    except ssl.SSLCertVerificationError as e:
        record.update(ok=False, reason="cert_invalid", error=str(e)[:200])
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        record.update(ok=False, reason="unreachable", error=str(e)[:200])
    return record


def main() -> int:
    out_dir = EVIDENCE_ROOT / utc_date()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "tailnet_portal.jsonl"
    record = probe()
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False))
    return 0 if record.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
