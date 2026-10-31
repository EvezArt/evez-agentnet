# EVEZ MYCELIUM — Hermes and EVEZ operations integration

## What this adds

EVEZ MYCELIUM is a shared Agent Skills-format operations layer for Hermes and OpenClaw. It routes tasks across the existing EVEZ architecture without duplicating agent runtimes or copying executable code into every repository.

- Hermes: reasoning and synthesis.
- OpenClaw: optional, scoped execution.
- EVEZ AgentNet: current orchestration and task queue.
- EVEZ-OS: event/evidence spine and operating contract.
- CAIN/WITNESS: contradiction review and provenance.

This is a software coordination layer, not an autonomous nonhuman entity or a self-replicating worm.

## Install the shared skill

From the root of an EVEZ AgentNet checkout:

    bash ops/install-evez-mycelium.sh

Default skill targets:

- Hermes: ~/.hermes/skills/evez-mycelium/SKILL.md
- OpenClaw: ~/.openclaw/workspace/skills/evez-mycelium/SKILL.md

Override either destination with HERMES_SKILLS_DIR or OPENCLAW_SKILLS_DIR. The installer refuses to overwrite a different existing skill unless EVEZ_INSTALL_OVERWRITE=1 is explicitly set; it saves a timestamped .bak copy before replacement.

The installer copies one instruction file. It does not create startup hooks, cron jobs, daemons, hidden persistence, credentials, or repository mutations.

## Run the operations loop

One bounded cycle from a shell outside Hermes:

    python3 ops/evez_autopilot.py --once

One inventory and queue cycle from a Hermes session:

    python3 ops/evez_autopilot.py --once --skip-hermes

Use --skip-hermes when already inside Hermes; otherwise the autopilot would spawn a second Hermes CLI process to analyze the first Hermes session's own request.

A finite watch is available only with explicit caps:

    python3 ops/evez_autopilot.py --watch --max-cycles 3 --max-runtime-seconds 5400

Limits: at most 12 cycles and 21,600 seconds. The outer deadline is checked between cycles; a cycle already in progress may finish after the deadline. Each Hermes/OpenClaw subprocess is bounded by EVEZ_ACTION_TIMEOUT_SECONDS (default 600; hard cap 900 seconds), and each GitHub request has its own timeout. The default invocation performs exactly one cycle.

## Execution gates

- OpenClaw execution remains disabled unless EVEZ_OPENCLAW_EXEC=1 is explicitly set.
- The OpenClaw task instructions restrict work to local/isolated low-risk investigation or preparing a patch; no remote push, merge, deployment, credential action, or destructive operation.
- Remote repository writes, release, production deployment, permissions, credentials, finance, deletion, and external communication remain approval-gated.
- Set EVEZ_AUTOPILOT_DISABLE=1 to stop the next cycle and prevent later major stages. This is not a substitute for terminating a subprocess already in progress.
- Keep the service's read-only setting enabled until identity, capability grants, endpoint allowlists, and policy adapter have all been independently verified.

## Evidence discipline

The autopilot's current local ledger uses SHA-256 over sorted compact JSON and links each event to its prior event hash. That is a local tamper-evident chain, not a signature, external anchor, WORM store, or RFC 8785 JCS implementation. Preserve those distinctions in reports.

The inventory currently filters private repositories from its results. A clean public inventory is not evidence that private repositories were inspected.

## Expected result

A completed cycle should leave:

- A redacted portfolio observation packet.
- A local append-only event record for the cycle.
- A timestamped task queue file.
- A latest-run summary showing Hermes/OpenClaw status and the queue path.

A generated task is a proposal, not permission to execute it. A successful API call is not proof that a release or deployment succeeded. The independent verifier must inspect the actual artifact and test results.

## Rollback and recovery

The skill installer preserves an existing file as a timestamped .bak copy when explicit overwrite is enabled. To revert, restore that backup or remove the new skill file. No code in this installer modifies repository history or running services.

For operational failures, preserve the current ledger, task packet, stdout/stderr, exact source revision, and test output before attempting repair. Stop after two failed repairs on the same defect and report BLOCKED with the next discriminating test.
