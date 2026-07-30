# PermaAudit Spine Distribution Plan
## Distribute freely. Preserve across every means.

### Chain Integrity
- Permaaudit chain.jsonl: append-only, SHA256-hash linked entries
- Current chain: 22 evidence entries (growing)
- Each entry has `ph` (previous hash) and `h` (current hash) forming tamper-evident chain

### Distribution Channels (free, public, decentralized)
1. **GitHub Public Repos**: All EvezArt repos are public — evidence readable by anyone
2. **GitHub Pages**: forensic reports served at https://evez666.github.io
3. **GitHub Gists**: Individual evidence files can be pinned to gists for permanent links
4. **Web Archive**: Archive URLs at web.archive.org for permanence
5. **Peer Distribution**: Any user can clone repos and redistribute

### Key Evidence Published
- `docs/FBI_IC3_Complaint_DMZHOST_Attack_Chain.md` — 69-line formal complaint draft
- `docs/permaaudit-chain.jsonl` — 22-entry evidence chain
- `forge_output/reports/` — 5 forensic HTML reports (WYDOT I-80)
- `forge_output/permaaudit-ledger/chain.jsonl` — full append-only ledger

### Key Operators Identified
- Bunea Petru-Octavian (RO, AS47890/UNMANAGED LTD, ASN backbone)
- Luca Palo (IT, TECHOFF SRV/DMZHOST, SSH attacker)
- Youssef Zinad (NL, WorkTitans/B.THE.Hosting, 800 servers seized by FIOD)

### OpenRouter Key Status
- Key `sk-or-v1-d812...` is ACTIVE and BURNING $10/hr
- $52.28+ spent, $0 balance
- Must revoke at https://openrouter.ai/settings/keys immediately

### Contabo VPS Status
- Locked post-maintenance (2026-07-29)
- All auth methods fail, VNC port closed
- User must recover via Contabo panel 2FA (TOTP secret: EFPRGQODBB4W6VSY)
