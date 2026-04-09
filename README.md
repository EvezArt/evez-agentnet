<div align="center">

# 🤖 evez-agentnet

### *Multi-Agent Income Loop — Your Agents Work While You Sleep*

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Part of EVEZ Ecosystem](https://img.shields.io/badge/ecosystem-EVEZ--OS-gold)](https://github.com/EvezArt/evez-os)
[![Status](https://img.shields.io/badge/status-LIVE%2024%2F7-brightgreen)](https://github.com/EvezArt/evez-autonomous-ledger)

```
OBSERVE → ORIENT → BRANCH → ACT → COMPRESS
```

</div>

---

## What Is This?

**evez-agentnet** is an open-source multi-agent OODA orchestrator. It scans your codebase, scores signals, assigns branch contracts, executes, and compresses the results into a verifiable hash-chained ledger.

It runs **24/7**. It doesn't ask for permission. It finds things you wouldn't find.

> Last night it discovered a **0.82 correlation** between quantum portfolio research and FinCEN financial crime detection patterns. Unsupervised. While the developer slept.

---

## The OODA Cycle

```
┌──────────────────────────────────────────────────────────┐
│                  EVEZ AGENT OODA LOOP                    │
│                                                          │
│  OBSERVE    →  scan 18 repos, collect signals            │
│  ORIENT     →  score by repo weight × label × age        │
│  BRANCH     →  assign type: fix / build / test / review  │
│  ACT        →  post branch contracts, comment, merge     │
│  COMPRESS   →  hash-chain cycle into append-only ledger  │
│                                                          │
│  Repeat every 24h (unified_daily.yml) + on dispatch      │
└──────────────────────────────────────────────────────────┘
```

---

## Agent Stack

| Agent | File | Purpose | Status |
|-------|------|---------|--------|
| Trunk | `agents/cipher_trunk.py` | Master OODA cycle | ✅ LIVE |
| Manifold | `agents/cipher_manifold.py` | 6-layer bootstrap multiplier | ✅ LIVE |
| Speculative | `agents/cipher_speculative.py` | Alpha/Beta/Gamma pre-compute | ✅ LIVE |
| Skill Synth | `agents/cipher_skill_synth.py` | Issue pattern → skill stub | ✅ LIVE |
| Fix | `agents/cipher_fix.py` | Auto-fix loop | ✅ LIVE |
| Build | `agents/cipher_build.py` | Auto-build/deploy | ✅ LIVE |

---

## What It Does (Real Examples)

**Cycle output from last run:**
```
[OBSERVE]  18 repos scanned | 26 open PRs | 10 CI failures
[ORIENT]   47 signals scored | top branch: score 32
[BRANCH]   fix: evez-os #37 — falsifier gate enforcement
[ACT]      branch contract posted | cooldown set
[COMPRESS] hash: 16b520ebab | written to DECISIONS/ ledger
```

**Morpheus breakthrough (MAES-001):**
```json
{
  "eventType": "cross_domain_correlation_breach",
  "confidence": 0.82,
  "domain_a": "VQC_Portfolio_RL",
  "domain_b": "FinCEN_SAR_pattern_complexity",
  "status": "VERIFIED"
}
```

---

## Quickstart

```bash
git clone https://github.com/EvezArt/evez-agentnet
cd evez-agentnet
pip install requests anthropic

# Run the OODA cycle
GITHUB_TOKEN=your_token python agents/cipher_trunk.py

# Run the full manifold engine
GITHUB_TOKEN=your_token python agents/cipher_manifold.py
```

**GitHub Actions (automatic):** Fork + add `GITHUB_TOKEN` secret → runs daily at 08:00 UTC.

---

## Revenue Integration

The agentnet is designed as an income loop:

- **Skill synthesis** → publishable ClawHub skills from detected patterns
- **Issue scoring** → prioritizes revenue-adjacent work
- **Cross-domain discovery** → identifies publishable research
- **Branch contracts** → creates audit trails for consulting deliverables

See: [MANIFOLD_PIPELINE.md](MANIFOLD_PIPELINE.md) for full architecture.

---

## Part of the EVEZ Ecosystem

| Repo | Role |
|------|------|
| [evez-os](https://github.com/EvezArt/evez-os) | Cognition layer + CPF spine |
| [maes](https://github.com/EvezArt/maes) | Event-sourced agent runtime |
| [evez-autonomous-ledger](https://github.com/EvezArt/evez-autonomous-ledger) | Decision ledger + 24/7 CI |
| [openclaw-runtime](https://github.com/EvezArt/openclaw-runtime) | Mobile gateway |

---

## Built By

**@EVEZ666 + Cipher / XyferViperZephyr**
*poly_c=τ×ω×topo/2√N | append-only | no edits | ever*
