# evez-agentnet

**Scan. Predict. Generate. Ship.**

Income-generating multi-agent swarm built on the EVEZ-OS spine.

Creator: Steven Crawford-Maggard (EVEZ666)  
Spine: [github.com/EvezArt/evez-os](https://github.com/EvezArt/evez-os)  
Status: R37 cross_agent_governance building

---

## What it does

| Module | Job | Output |
|--------|-----|--------|
| `scanner/` | Pull live signals (jobs, markets, GitHub, Twitter trends, Polymarket) | `scan_results.jsonl` |
| `predictor/` | Rank opportunities, synthesize signals (Groq llama-3.3-70b) | `predictions.jsonl` |
| `generator/` | Draft deliverables (reports, tweets, Gumroad products, code) | `drafts/` |
| `shipper/` | Post to Twitter, upload to Gumroad, commit to GitHub | `ship_log.jsonl` |
| `worldsim/` | Internal economy: agents bid on tasks, reputation staking | `worldsim_state.json` |
| `spine/` | EVEZ provenance: append-only events, hash chain, replay | `spine.jsonl` |

## Architecture

```
evez-agentnet/
  scanner/
    sources/          # polymarket.py, github_trending.py, jobs.py, twitter_trends.py
    scan_agent.py     # main scanner loop
  predictor/
    groq_synth.py     # Groq llama synthesis + ranking
    predict_agent.py
  generator/
    report_gen.py     # markdown reports
    tweet_gen.py      # twitter threads
    gumroad_gen.py    # product descriptions + pricing
    code_gen.py       # code artifacts
    generate_agent.py
  shipper/
    twitter_ship.py
    gumroad_ship.py
    github_ship.py
    ship_agent.py
  worldsim/
    economy.py        # budget/resource/reputation state
    agent_market.py   # agents bid on tasks
    staking.py        # reputation staking = safety basin
    sim_engine.py
  spine/
    spine.py          # append-only JSONL writer
    hash_chain.py     # sha256 commitment chain
    replay.py         # deterministic replay
  orchestrator.py     # main loop: scan -> predict -> generate -> ship
  config.py           # env vars, API keys, targets
  requirements.txt
```

## Revenue Loop

```
scan() -> rank_opportunities() -> generate_deliverable() -> ship() -> earn()
```

One full loop runs every 30 minutes (synced with evez-os hyperloop).

## Termux (Android) Setup

```bash
pkg install python git
git clone https://github.com/EvezArt/evez-agentnet
cd evez-agentnet
pip install -r requirements.txt
cp config.example.env .env
# Add your API keys to .env
python orchestrator.py
```

## Server Setup

```bash
git clone https://github.com/EvezArt/evez-agentnet
cd evez-agentnet
pip install -r requirements.txt
cp config.example.env .env
# Add your API keys
crontab -e
# Add: */30 * * * * cd /path/to/evez-agentnet && python orchestrator.py >> logs/run.log 2>&1
```


### Secret Level Autoplay (OpenClaw + EVEZ Lord.exe)

Run the recursive game sim until secret levels unlock and spawn living entities:

```bash
python -m worldsim.play_secret_levels
```

This writes `worldsim/secret_levels_state.json` with unlocked levels and spawned entities.

## WorldSim: Reputation Staking

Agents bid on tasks using a budget. Lying (hallucinating, low sigma_f output) costs reputation.
Reputation IS the safety basin — maps directly to evez-os `truth_plane`:

| Reputation | Maps to | Allowed actions |
|-----------|---------|-----------------|
| >= 0.80 | CANONICAL | all |
| 0.60-0.80 | VERIFIED | generate + ship |
| 0.40-0.60 | HYPER | generate only |
| < 0.40 | THEATRICAL | blocked, evidence-seeking |


## Extensions and adapters

`evez-agentnet` currently ships extension-like adapters under `browser_agent/`:

- `browser_agent/tasks/groq_login.py` — Hyperbrowser automation task to rotate/recover GROQ keys and write repo secrets.
- `browser_agent/tasks/twitter_bearer.py` — Hyperbrowser automation task to recover Twitter bearer token and write repo secrets.
- `browser_agent/otp_relay.py` — Gmail OTP/magic-link relay used by browser tasks.
- `browser_agent/credential_vault.py` — GitHub Actions secret writer (`GITHUB_REPO_OWNER`/`GITHUB_REPO_NAME` override supported).

### Smoke tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## License

Copyright © Steven Crawford-Maggard (EVEZ666). All rights reserved.  
Commercial use requires license: rubikspubes69@gmail.com
