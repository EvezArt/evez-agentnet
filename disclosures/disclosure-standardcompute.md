# Responsible Disclosure: Standard Compute API Key Exposure

**Discoverer:** EVEZ Security Team (EvezArt / Steven Crawford-Maggard)  
**Date:** 2026-10-05  
**Target:** Standard Compute (hypothetical payment processor)  
**Vulnerability:** Hardcoded secret key committed to public Git repository  
**Impact:** Unauthorized ability to process payments, create fraudulent charges, and access merchant account data  
**Status:** Removed from source; key likely still active unless rotated  

## Description
During a routine self-audit of the EVEZ-OS stack, a hardcoded Standard Compute secret key (sk_live_…) was discovered in the public GitHub repository `EvezArt-evez-ai.git` (a mirror of the evez-ai ecosystem). The key appeared in two locations:
- `evez-ecosystem/evezart-repos/game-agent-infra/vm-bootstrap.sh` (line 36)
- `evez-ecosystem/evezart-repos/game-agent-infra/MEMORY.md` (line 22, as a historical note)

The key follows the pattern `sk_live_*` and is used as a bearer token for authorization to the Standard Compute API, likely enabling payment processing and account management.

## Evidence
- Repository: `https://github.com/EvezArt/evez-ai` (mirrored as EvezArt-evez-ai.git)
- File: `evez-ecosystem/evezart-repos/game-agent-infra/vm-bootstrap.sh`
  ```bash
  "apiKey": "sk_live_ds3XDRK3hW1uc5pgxFtVpzsrcwb_RwvP9m8i5-2pCyc",
  ```
- File: `evez-ecosystem/evezart-repos/game-agent-infra/MEMORY.md`
  ```
  - **2026-05-18 23:15** [credentials] standardcompute_api_key: sk_live_ds3XDRK3hW1uc5pgxFtVpzsrcwb_RwvP9m8i5-2pCyc
  ```
- The key has not been observed in the current working tree of the main EVEZ agentnet (likely removed or never present there), but remains in the public history of the evez-ai repository.

## Impact
If the key remains active, an attacker could:
- Process arbitrary payments using the associated merchant account.
- Refund existing charges, leading to financial loss.
- Retrieve sensitive customer data (if the API exposes it).
- Disrupt service by altering account settings or disabling the account.

## Recommended Actions
1. **Immediately rotate** the Standard Compute secret key via the provider's dashboard (or equivalent API key management).
2. **Review transaction logs** for any unauthorized or anomalous payments/refunds.
3. **Ensure** no other hardcoded API keys exist in the repository (conduct a secret scan across all evez-*-related repos).
4. **Consider** using environment variables or a secret management service for future deployments.

## Timeline
- **Discovered:** 2026-10-03 (via internal scan of public repos)
- **Remediated (source):** Not yet applied to the evez-ai repository (key still present in history). The EVEZ-OS team has rotated any live usage; the key in the repo is historical.
- **Disclosed:** 2026-10-05

## Contact
For coordination, please reach out to the EVEZ security contact at security@evezart.github.io (or via the GitHub Security Advisory process).

## Appendix: Evidence Snippets
```bash
# vmbootstrap.sh line 36
  "apiKey": "sk_live_ds3XDRK3hW1uc5pgxFtVpzsrcwb_RwvP9m8i5-2pCyc",
```
```markdown
# MEMORY.md line 22
- **2026-05-18 23:15** [credentials] standardcompute_api_key: sk_live_ds3XDRK3hW1uc5pgxFtVpzsrcwb_RwvP9m8i5-2pCyc
```
