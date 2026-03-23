# EvezArt plugin/extension/skill audit

Scope: plugin, skill, adapter, and extension-facing packages discoverable from repository root manifests via GitHub API metadata.

## Inventory matrix

| Repository | Type | Host runtime | Manifest / package metadata | Entrypoint/install surface | Status |
|---|---|---|---|---|---|
| evez-os | skill package / core runtime extension surface | Python + ClawHub/OpenClaw-compatible skill host conventions | `SKILL.md` at repo root | skill install surface documented in repo | active canonical |
| evez-agentnet | adapter/extensions (browser automation tasks) | Python runtime | `requirements.txt` | `browser_agent/tasks/*.py`, `orchestrator.py` | active |
| agentvault | plugin/adapter package | Python | `requirements.txt` | likely module/CLI entrypoint (needs repo-local inspection) | active |
| evez666-arg-canon | extension package | Python | `requirements.txt` | likely module/CLI entrypoint (needs repo-local inspection) | active |
| moltbot-live | plugin/bot package | Python | `requirements.txt`, `Dockerfile` | docker/python run surface | active |
| crawhub (fork) | extension host adapter | TypeScript | `package.json`, `vercel.json` | npm/vercel app surface | fork/wrapper |
| openclaw (fork) | host runtime/control plane | TypeScript | `package.json`, `Dockerfile` | npm/docker host surface | fork/host |
| perplexity-py (fork) | API adapter SDK | Python | `pyproject.toml` | python package install/import | fork/adapter |

### Experimental/needs deeper verification (insufficient root metadata to assert install path)

- `evez-net`, `evez-os-v2`, `evez-sim`, `blockche`, `polymarket-speedrun`, `Evez666`, `metarom`, `lord-evez*`.

These should be treated as experimental for extension interoperability until each repository's entrypoint and runtime contract is validated with repo-local tests.

## Naming/versioning findings

- `evez-*` naming is mostly consistent, but extension surfaces are split between Python (`requirements.txt`) and TypeScript (`package.json`) ecosystems.
- Cross-repo extension compatibility metadata is not centralized; each repo should expose a small compatibility matrix (host runtime, tested versions, install command, smoke test command).

## Improvements implemented in this repository (`evez-agentnet`)

1. **Scanner adapter hardening**: GitHub trending search now uses safe query encoding (`quote_plus`) with rolling date helper.
2. **Credential vault portability + dependency correctness**: repo owner/name are now environment-overridable (`GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`) and `PyNaCl` is explicitly declared.
3. **Extension smoke-test baseline + docs standardization**: added `tests/test_extensions_smoke.py` and documented extension surfaces + smoke test command in `README.md`.

## Next cross-repo extension actions (recommended)

1. Add a minimal `EXTENSION_COMPAT.md` to each extension/plugin repo with runtime, install command, entrypoint, and smoke-test command.
2. Add one smoke test workflow per extension repo (`python -m unittest` or `npm test`) to prevent manifest drift.
3. Standardize versioning fields (`version`, changelog policy, host compatibility matrix) across Python and TypeScript extension packages.
