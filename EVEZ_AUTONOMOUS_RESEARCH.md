# EVEZ Autonomous Research / Cleanup Control Plane

Role split:
- EVEZ spine: immutable evidence and provenance.
- Hermes (Nous Research): reasoning and synthesis backend on the local machine.
- OpenClaw: execution and tool orchestration on the local machine.
- GitHub: observation surface and, only after policy gates, mutation surface.

Safety boundary:
Observation, hashing, classification, report generation, and sandbox tests may run automatically.
Credential rotation, deletion of repository history, production deployment, external communications, and other irreversible actions require explicit human authorization.

Highest-priority current findings:
1. Public exposure audit identifies live-shaped Supabase service_role and ClawHub token material in the public corpus. Rotate before treating the corpus as trusted.
2. evez-ai contains a nested evez-ecosystem/evezart-repos mirror. This is a direct duplication/drift surface.
3. evez-liminal contains a committed .venv; remove from tracking and ignore it.
4. evez-os contains .pat_verify.txt; treat as a credential-risk artifact and rotate any credential represented by it before assuming safety.
5. evez-os/live-status.json is stale relative to current verified runtime state and should not be presented as live telemetry.
6. Public documentation contains quantitative and capability claims that need evidence links or explicit PROPOSED/HISTORICAL labels.
7. Multiple OpenClaw/EVEZ/Hermes repos overlap functionally and need consolidation mapping before destructive cleanup.

Autonomous cycle:
DISCOVER -> SNAPSHOT -> HASH -> CLASSIFY -> TEST -> CONTRADICT -> PACKAGE -> PROPOSE -> SANDBOX -> RECHECK

Never rewrite historical evidence to make a new state look old. New reality creates a new branch/event.

Epistemic doctrine:
CLAIMED != MEASURED != REPLICATED != EXPLAINED
PROVENANCE != TRUTH
UNKNOWN remains UNKNOWN until evidence promotes it.