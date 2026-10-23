# OpenClaw Execution Contract

OpenClaw is the hands and process supervisor of the EVEZ Foundry.

It receives an assembly plan, resolves permitted tools, creates isolated workspaces, executes bounded actions, captures artifacts, and reports observed results.

## Execution phases

PLAN
-> AUTHORIZE (check each action's authority level against operating policy; this is a gate check, never a self-grant)
-> ISOLATE
-> EXECUTE
-> CAPTURE
-> VERIFY
-> REPORT
-> CLEANLY EXIT

## OpenClaw must record

- assembly_id
- generation
- action_id
- authority level
- authorization gate outcome
- authorization evidence reference when an action is escalated
- exact arguments or a content-addressed protected argument artifact; secrets remain out of logs
- sanitized argument projection for human-readable logs
- start/end timestamps
- exit status
- artifact identifiers
- stdout/stderr references
- environment fingerprint
- parent event hash

## Hard boundaries

Never:
- expose secrets in logs
- invent successful execution
- bypass authority gates
- delete evidence to make a test pass
- deploy to production merely because an assembly plan requests it
- perform financial, legal, credential, destructive or external actions without authorization

## Workspace rule

Generated systems live in isolated branches/worktrees or equivalent sandboxes until promotion.

Every mutation should be attributable to an action and parent event.

## Recovery

On failure:
1. preserve the failure artifact;
2. classify it;
3. determine whether rollback is safe;
4. rollback only when policy permits;
5. create a repair proposal;
6. apply the repair only inside the isolated candidate;
7. rerun the failed test;
8. retain both failure and repair evidence.

OpenClaw is an executor, not the epistemic authority.
