# Responsible Disclosure: ClawHub API Token Exposure

**Discoverer:** EVEZ Security Team (EvezArt / Steven Crawford-Maggard)  
**Date:** 2026-10-05  
**Target:** ClawHub (https://clawhub.ai)  
**Vulnerability:** Hardcoded API token committed to public Git repository  
**Impact:** Unauthorized access to ClawHub API – potential abuse of skill injection, data exfiltration, and service disruption  
**Status:** Removed from source; token likely still active unless rotated  

## Description
During a routine self-audit of the EVEZ-OS stack, a hardcoded ClawHub API token (clh_…) was discovered in the public GitHub repository `EvezArt/evez-atlas`. The token was committed to the file `evez-os-sensors/self_interrogation.py`. The ClawHub token grants bearer-token access to the ClawHub API, allowing arbitrary skill invocation and data manipulation.

## Evidence
- Repository: `https://github.com/EvezArt/evez-atlas`
- Commit history (prior to remediation) contained the literal token.
- Current state (as of 2026-10-05) shows no token literal; the file now uses environment variables or placeholders.
- Audit logs from EVEZ-OS watchdog (exposure.jsonl, 2026-10-03) recorded multiple CRITICAL findings for `clawhub_token` across test files and the watchdog itself.

## Impact
If the token remains active, an attacker could:
- Invoke arbitrary skills on the ClawHub platform, potentially incurring costs or performing malicious actions.
- Read or modify skill configurations and data associated with the EVEZ account.
- Use the token to pivot to other services if the token is reused elsewhere.

## Recommended Actions
1. **Immediately rotate** the ClawHub API token via the ClawHub account settings.
2. **Review audit logs** for any unexpected skill invocations or API usage from unknown sources.
3. **Ensure** no other hardcoded credentials exist in the repository (conduct a secret scan).
4. **Consider** restricting the token's scope if ClawHub supports fine-grained permissions.

## Timeline
- **Discovered:** 2026-10-03 (via internal watchdog)
- **Remediated (source):** 2026-10-03 (token removed from source)
- **Disclosed:** 2026-10-05

## Contact
For coordination, please reach out to the EVEZ security contact at security@evezart.github.io (or via the GitHub Security Advisory process).

## Appendix: Excerpt from EVEZ-OS Exposure Log (2026-10-03)
```json
{
  "check": "secrets",
  "context": {
    "file": "test_exposure_scanner.py",
    "line_count": 1,
    "lines": [19],
    "root": "/root/evez-agentnet"
  },
  "detail": "credential-shaped match on disk (value withheld). Removal from the tree does NOT revoke it -- rotate at the provider.",
  "errored": false,
  "fingerprint": "96fc905bee899c89",
  "kind": "clawhub_token",
  "severity": "CRITICAL",
  "ts": "2026-10-03T08:35:39+02:00",
  "where": "/root/evez-agentnet:test_exposure_scanner.py:19"
}
```
