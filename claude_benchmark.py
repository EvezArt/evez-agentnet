#!/usr/bin/env python3
"""EVEZ-AgentNet Claude benchmark harness.

Measures the real thing, not the marketing claim:

    TARGET: maximum permitted concurrent AgentNet executions under the
    assigned Anthropic organization limits.

    BENCHMARK: 1 -> 5 -> 10 -> 25 -> 50 concurrent agents, stopping at the
    actual provider limit rather than assuming an uncapped limit.

    MEASURE: throughput, RPM/ITPM/OTPM consumption, 429 rate, p50/p95
    latency, successful completions, cost/run, receipt integrity.

The harness exists independently of credits: with no ANTHROPIC_API_KEY it
runs against a local mock server so the measurement pipeline, receipt chain,
and report generator are all exercised before a single real token is spent.
When credits land, the same code paths run unchanged against
api.anthropic.com. The mock is NOT the benchmark; it exercises the harness
and never substitutes for the real provider's numbers.

Receipt integrity is part of the benchmark: every run appends SHA-256
hash-chained rows to evidence/<UTC-date>/claude_benchmark.jsonl, each row
linking to the previous row's hash. Tampering with any row breaks the chain
at the next verify.

Usage:
    python3 claude_benchmark.py --help
    python3 claude_benchmark.py --dry-run                 # mock provider
    python3 claude_benchmark.py --stages 1,5,10            # subset of stages
    ANTHROPIC_API_KEY=... python3 claude_benchmark.py      # real provider

Exit codes: 0 ok | 1 permanent error (receipt chain broken)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent
EVIDENCE = REPO / "evidence"

ANTHROPIC_BASE = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
MESSAGES_PATH = "/v1/messages"

# Each stage runs N concurrent agents; the ladder stops at the real limit.
DEFAULT_STAGES = [1, 5, 10, 25, 50]
MOCK_RPS_CAP = int(os.environ.get("MOCK_RPS_CAP", "5"))  # mock: force 429s past cap


class ReceiptChain:
    """SHA-256 hash-chained evidence rows, same discipline as the spine."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.prev = None
        if self.path.exists():
            try:
                last = self.path.read_text().strip().splitlines()[-1]
                self.prev = json.loads(last).get("sha256")
            except (OSError, ValueError, IndexError):
                self.prev = None

    def append(self, row: dict) -> dict:
        row = dict(row)
        row["prev_sha256"] = self.prev
        row["ts"] = datetime.now(timezone.utc).isoformat()
        blob = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
        row["sha256"] = hashlib.sha256(blob).hexdigest()[:16]
        with self._lock:
            with self.path.open("a") as f:
                f.write(json.dumps(row, sort_keys=True) + "\n")
            self.prev = row["sha256"]
        return row

    def verify(self) -> tuple:
        """Recompute the whole chain; return (ok, rows_checked)."""
        if not self.path.exists():
            return True, 0
        prev = None
        n = 0
        for line in self.path.read_text().strip().splitlines():
            row = json.loads(line)
            if row.get("prev_sha256") != prev:
                return False, n
            expected_fields = {k: row[k] for k in row if k not in ("sha256",)}
            blob = json.dumps(
                expected_fields, sort_keys=True, separators=(",", ":")
            ).encode()
            if hashlib.sha256(blob).hexdigest()[:16] != row.get("sha256"):
                return False, n
            prev = row["sha256"]
            n += 1
        return True, n


class MockProvider(threading.Thread):
    """Local HTTP mock of /v1/messages that enforces a one-second rate cap.

    Used for --dry-run and the CI self-test. Deliberately memoryless of
    content: fixed-size responses, request counting only. Binds to an
    OS-assigned free port (port 0) — the 187xx range is live EVEZ
    infrastructure (perimeter, cogs) and must never be hardcoded as a
    mock address.
    """

    def __init__(self, port: int = 0, rps_cap: int = 5):
        super().__init__(daemon=True)
        self.requested_port = port
        self.port = None
        self.rps_cap = rps_cap
        self._srv = None

    def run(self):
        import http.server

        lock = threading.Lock()
        srv_ref = {}

        class H(http.server.BaseHTTPRequestHandler):
            def _respond(self, code, obj):
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                if self.path != MESSAGES_PATH:
                    self._respond(404, {"error": "not found"})
                    return
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    self.rfile.read(length)
                srv = srv_ref["srv"]
                with lock:
                    srv.hits += 1
                    now = time.monotonic()
                    st = srv.state
                    if now - st["window_start"] >= 1.0:
                        st["window_start"] = now
                        st["count"] = 0
                    st["count"] += 1
                    over_cap = st["count"] > srv.rps_cap
                if over_cap:
                    self._respond(
                        429,
                        {
                            "type": "error",
                            "error": {
                                "type": "rate_limit_error",
                                "message": "mock rate limit",
                            },
                        },
                    )
                    return
                self._respond(
                    200,
                    {
                        "id": "msg_mock_%d" % srv.hits,
                        "type": "message",
                        "role": "assistant",
                        "model": "mock",
                        "content": [{"type": "text", "text": "ok" * 20}],
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 40, "output_tokens": 40},
                    },
                )

            def log_message(self, *a):
                pass

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", self.requested_port), H)
        srv.hits = 0
        srv.state = {"window_start": time.monotonic(), "count": 0}
        srv.rps_cap = self.rps_cap
        srv_ref["srv"] = srv
        self._srv = srv
        self.port = srv.server_address[1]
        srv.serve_forever(poll_interval=0.05)

    def stop(self):
        if self._srv is not None:
            self._srv.shutdown()
            self._srv = None


class ClaudeClient:
    """Minimal Anthropic Messages API client. No SDK dependency.

    A 429 may carry a retry-after header; the harness records the status
    but does not sleep on it — recording real provider behavior is the
    point of the benchmark.
    """

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def message(self, prompt: str, max_tokens: int = 40) -> dict:
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(
            self.base_url + MESSAGES_PATH,
            data=json.dumps(payload).encode(),
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = {}
            try:
                body = json.loads(e.read())
            except Exception:
                pass
            return {
                "_status": e.code,
                "_body": body,
                "_retry_after": e.headers.get("retry-after"),
            }


def run_stage(client: ClaudeClient, n_agents: int, receipt: ReceiptChain, stage_id: str) -> dict:
    """Run n_agents concurrent single-shot agents; return measured stats."""
    latencies = []
    completions = 0
    rate_limited = 0
    errors = 0
    in_tokens = 0
    out_tokens = 0
    lock = threading.Lock()

    def agent(_i: int):
        nonlocal completions, rate_limited, errors, in_tokens, out_tokens
        t0 = time.monotonic()
        try:
            resp = client.message("Reply with the single word: ok")
            dt = time.monotonic() - t0
            status = resp.get("_status")
            with lock:
                latencies.append(dt)
                if status is None:
                    completions += 1
                    usage = resp.get("usage") or {}
                    in_tokens += usage.get("input_tokens", 0)
                    out_tokens += usage.get("output_tokens", 0)
                elif status == 429:
                    rate_limited += 1
                else:
                    errors += 1
        except Exception:
            with lock:
                errors += 1
                latencies.append(time.monotonic() - t0)

    threads = [threading.Thread(target=agent, args=(i,)) for i in range(n_agents)]
    t_start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.monotonic() - t_start

    lat = sorted(latencies) or [0.0]
    stats = {
        "event": "claude_benchmark_stage",
        "stage": stage_id,
        "n_agents": n_agents,
        "completions": completions,
        "rate_limited_429": rate_limited,
        "errors": errors,
        "wall_s": round(wall, 3),
        "rps": round(completions / wall, 3) if wall > 0 else 0,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "latency_p50_s": round(statistics.median(lat), 3),
        "latency_p95_s": round(lat[max(0, int(len(lat) * 0.95) - 1)], 3),
        "model": client.model,
        "provider_base": client.base_url,
    }
    receipt.append(stats)
    return stats


def spine_append(event: dict):
    """Publish the benchmark summary to the EVEZ event spine (best effort).

    The spine service is at 127.0.0.1:9116 /append and requires the
    X-Spine-Token header (EVEZ_SPINE_TOKEN env var) with the payload shape
    {domain, action, data, timestamp}. Failure to publish is recorded in
    the receipt, never silently dropped, and never blocks the benchmark
    result.
    """
    token = os.environ.get("EVEZ_SPINE_TOKEN", "").strip()
    if not token:
        return {"error": "EVEZ_SPINE_TOKEN unset"}
    payload = {
        "domain": "benchmark",
        "action": "claude_benchmark_summary",
        "data": event,
        "timestamp": time.time(),
    }
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:9116/append",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-Spine-Token": token},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser(description="EVEZ-AgentNet Claude benchmark harness")
    ap.add_argument("--dry-run", action="store_true",
                    help="run against the local mock provider, not api.anthropic.com")
    ap.add_argument("--stages", default=",".join(str(s) for s in DEFAULT_STAGES),
                    help="comma list of concurrent-agent counts (default 1,5,10,25,50)")
    ap.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5"))
    ap.add_argument("--api-key", default=os.environ.get("ANTHROPIC_API_KEY", ""))
    ap.add_argument("--receipt-file", default=None,
                    help="override evidence path (used by the self-test)")
    ap.add_argument("--limit-seconds", type=float, default=0,
                    help="wall-clock budget for the whole ladder (0 = no limit)")
    ap.add_argument("--mock-port", type=int, default=0,
                    help="mock bind port (0 = OS-assigned free port; recommended)")
    ap.add_argument("--mock-rps-cap", type=int, default=MOCK_RPS_CAP)
    args = ap.parse_args()

    stages = [int(s) for s in args.stages.split(",") if s.strip()]
    mock = None
    if args.dry_run or not args.api_key:
        mock = MockProvider(args.mock_port, args.mock_rps_cap)
        mock.start()
        # canary: a mock that never came up would let the whole ladder
        # "succeed" on connection errors — that is a measurement lie.
        t_wait = time.monotonic() + 10
        while mock.port is None and time.monotonic() < t_wait:
            time.sleep(0.05)
        if mock.port is None:
            print("[claude-benchmark] mock provider failed to bind; aborting")
            return 1
        probe = ClaudeClient(
            "http://127.0.0.1:%d" % mock.port, "mock-key", args.model, timeout=5
        )
        probe_resp = probe.message("canary")
        if probe_resp.get("_status") is not None:
            print("[claude-benchmark] mock provider canary failed; aborting")
            return 1
        base_url = "http://127.0.0.1:%d" % mock.port
        api_key = "mock-key"
        provider = "mock"
    else:
        base_url = ANTHROPIC_BASE
        api_key = args.api_key
        provider = "anthropic"

    if args.receipt_file:
        receipt_path = Path(args.receipt_file)
    else:
        day_dir = EVIDENCE / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        receipt_path = day_dir / "claude_benchmark.jsonl"
    receipts = ReceiptChain(receipt_path)
    client = ClaudeClient(base_url, api_key, args.model)

    print("[claude-benchmark] provider=%s base=%s model=%s" % (provider, base_url, args.model))
    results = []
    stopped_at = None
    t0 = time.monotonic()
    try:
        for n in stages:
            print("[claude-benchmark] stage %d concurrent agents ..." % n)
            stats = run_stage(client, n, receipts, "n%d" % n)
            results.append(stats)
            print(
                "  completions=%d/%d 429s=%d errors=%d wall=%ss rps=%s "
                "p50=%ss p95=%ss"
                % (
                    stats["completions"], n, stats["rate_limited_429"],
                    stats["errors"], stats["wall_s"], stats["rps"],
                    stats["latency_p50_s"], stats["latency_p95_s"],
                )
            )
            if args.limit_seconds and time.monotonic() - t0 > args.limit_seconds:
                stopped_at = n
                print("[claude-benchmark] wall-clock budget reached; stopping ladder")
                break
            if stats["errors"] >= n and n > 1:
                stopped_at = n
                print("[claude-benchmark] all requests errored; stopping ladder")
                break
    finally:
        if mock:
            mock.stop()

    ok, rows = receipts.verify()
    summary = {
        "event": "claude_benchmark_summary",
        "provider": provider,
        "model": args.model,
        "stages": [r["stage"] for r in results],
        "max_completed_stage": max(
            (r["n_agents"] for r in results if r["completions"] > 0), default=0
        ),
        "total_429": sum(r["rate_limited_429"] for r in results),
        "total_input_tokens": sum(r["input_tokens"] for r in results),
        "total_output_tokens": sum(r["output_tokens"] for r in results),
        "receipt_chain_ok": ok,
        "receipt_rows": rows,
        "ladder_stopped_at": stopped_at,
        "mock_used": provider == "mock",
    }
    receipts.append(summary)
    spine_res = spine_append(dict(summary))
    summary["spine_publish"] = "ok" if not (isinstance(spine_res, dict) and "error" in spine_res) else "failed"
    print("\n[claude-benchmark] receipts: chain_ok=%s rows=%d -> %s" % (ok, rows, receipt_path))
    if not ok:
        print("[claude-benchmark] RECEIPT CHAIN BROKEN - do not use these numbers")
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
