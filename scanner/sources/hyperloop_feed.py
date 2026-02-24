#!/usr/bin/env python3
"""
evez-agentnet/scanner/sources/hyperloop_feed.py
Pulls live state from EvezArt/evez-os hyperloop_state.json.
Surfaces watchlist, x_signal_buffer, probe results as scan signals.
"""
import os, json, logging, urllib.request, base64
log = logging.getLogger("agentnet.scanner.hyperloop")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HYPERLOOP_REPO = "EvezArt/evez-os"
STATE_PATH = "workspace/hyperloop_state.json"


def scan() -> list:
    try:
        state = _fetch_state()
        return _extract_signals(state)
    except Exception as e:
        log.debug(f"Hyperloop feed: {e}")
        return []


def _fetch_state() -> dict:
    url = f"https://api.github.com/repos/{HYPERLOOP_REPO}/contents/{STATE_PATH}"
    headers = {"User-Agent": "evez-agentnet/1.0", "Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    return json.loads(base64.b64decode(data["content"]).decode())


def _extract_signals(state: dict) -> list:
    signals = []

    # Watchlist: upcoming fire rounds
    watchlist = state.get("watchlist", {})
    for key, val in watchlist.items():
        signals.append({
            "source": "hyperloop_watchlist",
            "type": "fire_prediction",
            "title": f"EVEZ-OS {key}: {val}",
            "opportunity": "twitter_thread",
            "evez_signal": True,
        })

    # New X capsules from semantic agent
    x_agent = state.get("x_semantic_agent", {})
    new_capsules = x_agent.get("new_this_run", 0)
    clusters = x_agent.get("clusters_hit", [])
    if new_capsules > 0:
        signals.append({
            "source": "hyperloop_x_capsules",
            "type": "x_semantic_signal",
            "title": f"{new_capsules} new X capsules — clusters: {', '.join(clusters)}",
            "opportunity": "twitter_thread",
            "new_capsules": new_capsules,
            "clusters": clusters,
            "evez_signal": True,
        })

    # Maturity milestone = narrative opportunity
    maturity = state.get("maturity", {})
    milestone = maturity.get("milestone", "")
    if milestone:
        signals.append({
            "source": "hyperloop_maturity",
            "type": "milestone_signal",
            "title": milestone,
            "opportunity": "twitter_thread",
            "v_global": state.get("V_global", 0),
            "current_round": state.get("current_round", 0),
            "evez_signal": True,
        })

    # Active probe = in-flight research result available
    for key, probe in state.get("r182_browser_jobs", {}).items():
        if probe.get("status") == "in-flight":
            signals.append({
                "source": "hyperloop_probe",
                "type": "probe_signal",
                "title": f"Probe in-flight: {key} job {probe.get('job_id', '')[:8]}",
                "opportunity": "twitter_thread",
                "evez_signal": True,
            })

    return signals
