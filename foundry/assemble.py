#!/usr/bin/env python3
"""EVEZ Agentic OS assembly compiler.

Builds deterministic candidate manifests from a capability graph.
All inferred capabilities remain PROPOSED until independently tested.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH = ROOT / "foundry" / "data" / "github_inventory_2026-10-05.json"

CORE_BY_CAPABILITY = {
    "evidence": ["evez-event-spine", "evez-evidence-runtime", "evez-witness", "evez-invariance-battery", "evez-agentnet"],
    "agent_runtime": ["openclaw-runtime", "evez-openclaw-deploy", "hermes-setup", "evez-agentnet"],
    "research_science": ["evez-phenomenologic", "evez-sim", "evez-benchmarks", "evez-autonomous-ledger"],
    "field_device": ["evez-openclaw-android", "evez-device-portal", "evez-meshnet"],
    "commerce": ["evez-commerce", "evez-outreach", "evez-revenue-engine"],
}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def load_graph(path):
    data = load_json(path)
    if data.get("schema") != "evez.capability.graph.v1":
        raise ValueError("unexpected capability graph schema")
    return data

def load_preset(path):
    data = load_json(path)
    if data.get("schema") != "evez.os.preset.v1":
        raise ValueError("unexpected preset schema")
    return data

def tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def score(repo, objective, required_caps):
    text = " ".join([
        repo.get("name", ""),
        repo.get("description", ""),
        " ".join(repo.get("capabilities", [])),
    ]).lower()
    wanted = tokens(objective)
    overlap = sum(1 for token in wanted if len(token) > 2 and token in text)
    caps = set(repo.get("capabilities", []))
    capability_bonus = 0
    for cap in required_caps:
        if cap in caps:
            capability_bonus += 12
    core_bonus = 8 if repo.get("name") in {n for values in CORE_BY_CAPABILITY.values() for n in values} else 0
    archive_penalty = 10 if repo.get("archived") else 0
    general_penalty = 3 if repo.get("capabilities") == ["general"] else 0
    return overlap * 5 + capability_bonus + min(len(caps), 8) + core_bonus - archive_penalty - general_penalty

def select(graph, objective, required_caps, limit=16):
    nodes = graph["nodes"]
    ranked = sorted(
        ((score(node, objective, required_caps), node) for node in nodes),
        key=lambda pair: (pair[0], -pair[1].get("size_kb", 0), pair[1]["name"]),
        reverse=True,
    )
    chosen = []
    seen = set()

    for points, node in ranked:
        if node["name"] in seen or points <= 0:
            continue
        chosen.append({
            "repo": node["full_name"],
            "capabilities": node["capabilities"],
            "score": points,
            "state": "PROPOSED",
            "basis": "repository metadata heuristic",
        })
        seen.add(node["name"])
        if len(chosen) >= limit:
            break

    for capability in required_caps:
        for name in CORE_BY_CAPABILITY.get(capability, []):
            if name in seen:
                continue
            node = next((item for item in nodes if item["name"] == name), None)
            if node:
                chosen.append({
                    "repo": node["full_name"],
                    "capabilities": node["capabilities"],
                    "score": "CORE_REQUIRED",
                    "state": "PROPOSED",
                    "basis": "assembly core registry",
                    "required_capability": capability,
                })
                seen.add(name)

    return chosen

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("objective", nargs="?", default=None)
    ap.add_argument("--preset", default=None)
    ap.add_argument("--graph", default=str(DEFAULT_GRAPH))
    ap.add_argument("--id", default=None)
    ap.add_argument("--generation", type=int, default=0)
    ap.add_argument("--out", default="data/evez-foundry/candidate.json")
    args = ap.parse_args()

    graph = load_graph(args.graph)
    preset = load_preset(args.preset) if args.preset else {}
    objective = preset.get("objective") or args.objective
    if not objective:
        raise SystemExit("provide an objective or --preset")

    required_caps = preset.get("capabilities", [])
    selected = select(graph, objective, required_caps)
    osid = preset.get("os_id") or args.id or (
        "evez-" + re.sub(r"[^a-z0-9]+", "-", objective.lower()).strip("-")[:48]
    )

    manifest = {
        "$schema": "foundry/OS_MANIFEST.schema.json",
        "os_id": osid,
        "generation": int(preset.get("generation", args.generation)),
        "objective": objective,
        "kernel": preset.get("kernel", "evez-foundry-kernel-v0"),
        "capabilities": sorted({cap for item in selected for cap in item["capabilities"]}),
        "agents": preset.get("agents", [
            "SCOUT", "HARVEST", "COMPILER", "EXPERIMENTER", "RUNNER",
            "WITNESS", "CAIN", "REPLICATOR", "SYNTHESIZER", "CARTOGRAPHER",
            "BUILDER", "CRITIC",
        ]),
        "tools": preset.get("tools", ["Hermes", "OpenClaw", "EVEZ Spine"]),
        "memory": preset.get("memory", ["event-spine", "candidate-state", "artifact-index"]),
        "tests": preset.get("tests", [
            "boot", "capability smoke", "authority gate",
            "evidence receipt", "failure injection", "replay",
        ]),
        "authority": preset.get("authority", {"maximum_autonomy": 5}),
        "evidence": preset.get("evidence", {
            "spine": "evez-event-spine",
            "promotion_ladder": [
                "UNKNOWN", "OBSERVED", "EXECUTABLE", "TESTED",
                "REPRODUCED", "VALIDATED", "PROMOTED",
            ],
        }),
        "recovery": preset.get("recovery", [
            "preserve failure receipt",
            "rollback isolated workspace",
            "replay failed test",
            "retain contradiction",
        ]),
        "selected_repositories": selected,
        "required_capabilities": required_caps,
        "preset_source": args.preset,
        "source_graph_digest": digest(graph),
        "planner_status": "PROPOSED",
        "doctrine": [
            "CLAIMED != MEASURED != REPLICATED != EXPLAINED",
            "PROVENANCE != TRUTH",
        ],
    }
    if "privacy" in preset:
        manifest["privacy"] = preset["privacy"]
    if "design_rule" in preset:
        manifest["design_rule"] = preset["design_rule"]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "out": str(out),
        "os_id": osid,
        "selected": len(selected),
        "required_capabilities": required_caps,
        "status": "PROPOSED",
        "graph_digest": manifest["source_graph_digest"],
    }, indent=2))

if __name__ == "__main__":
    main()
