# Responsible Disclosure: Supabase Service Role Key Exposure

**Discoverer:** EVEZ Security Team (EvezArt / Steven Crawford-Maggard)  
**Date:** 2026-10-05  
**Target:** Supabase (https://supabase.com)  
**Vulnerability:** Hardcoded service_role key committed to public Git repository  
**Impact:** Full bypass of row-level security (RLS) – unrestricted read/write access to all project data  
**Status:** Removed from source; key likely still active unless rotated  

## Description
During a routine self-audit of the EVEZ-OS stack, a hardcoded Supabase service_role key was discovered in the public GitHub repository `EvezArt/evez-atlas`. The key was committed to the file `functions/evezPersist.ts` (line 4) and also referenced in `functions/evezCorpusStore.ts`. The service_role key bypasses Supabase row-level security, granting full administrative access to the associated Supabase project.

## Evidence
- Repository: `https://github.com/EvezArt/evez-atlas`
- Commit history (prior to remediation) contained the literal key.
- Current state (as of 2026-10-05) shows the key replaced with environment-variable lookup:
  ```ts
  const url = Deno.env.get('SUPABASE_URL')
  const key = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  ```
- Audit logs from EVEZ-OS watchdog (exposure.jsonl, 2026-10-03) recorded multiple CRITICAL findings for `supabase_service_role` across various files (see attached excerpt).

## Impact
If the key remains active, an attacker could:
- Read all data in the Supabase project, including sensitive user information.
- Modify or delete any data.
- Perform administrative operations (e.g., enable/disable features, alter schemas).

## Recommended Actions
1. **Immediately rotate** the Supabase service_role key via the Supabase dashboard (Project Settings → API).
2. **Audit logs** for any unexpected access from unknown IPs.
3. **Ensure** no other hardcoded credentials exist in the repository (conduct a secret scan).
4. **Consider** enabling Supabase audit logging and setting up alerts for anomalous queries.

## Timeline
- **Discovered:** 2026-10-03 (via internal watchdog)
- **Remediated (source):** 2026-10-03 (key removed from source, replaced with env var)
- **Disclosed:** 2026-10-05

## Contact
For coordination, please reach out to the EVEZ security contact at security@evezart.github.io (or via the GitHub Security Advisory process).

## Appendix: Excerpt from EVEZ-OS Exposure Log (2026-10-03)
```json
{
  "check": "secrets",
  "context": {
    "file": "functions/evezPersist.ts",
    "line_count": 1,
    "lines": [4],
    "root": "/root/repos/evez-atlas"
  },
  "detail": "credential-shaped match on disk (value withheld). Removal from the tree does NOT revoke it -- rotate at the provider.",
  "errored": false,
  "fingerprint": "f999a28db30b297d",
  "kind": "supabase_service_role",
  "severity": "CRITICAL",
  "ts": "2026-10-03T08:35:44+02:00",
  "where": "/root/repos/evez-atlas:functions/evezPersist.ts:4"
}
```
