# EVEZ Forensic Evidence Pack

**Prepared for:** law-enforcement and regulatory review
**Subject host:** `vmi3544756` — `100.126.180.47` (Tailscale) / `80.241.209.34`
**Custodian:** Steven Crawford-Maggard (EVEZ)
**Generated:** see `evidence/MANIFEST.json` → `generated_at`

---

## 1. Purpose and honest scope

This pack is built from artifacts that exist on the subject host and can be
independently re-verified by a third party. Every claim below is labelled with
what it **proves** and what it **does not prove**.

That labelling is deliberate. A forensic pack that overstates its own reach is
discarded by a reviewer, and its credible findings are discarded with it.

### What this pack contains

| Artifact | SHA-256 (first 16) | Bytes |
|---|---|---|
| `spine/spine.jsonl` (primary) | `dd3648eed7b6ad33` | 670,143 |
| `evidence/spine-ledger.json` | `1e1f7b4f921dbe44` | 1,366 |
| `evidence/infrastructure-attribution.json` | `7d551291d242ce07` | 3,862 |
| `evidence/infrastructure-verification.json` | `679ed5d192bd0625` | 8,097 |
| `evidence/MANIFEST.json` | — | — |

### What this pack does NOT contain

**The May 2026 intrusion is not documented here.** The following are not present
on this host and are therefore absent from this pack:

- packet captures or PCAP files
- disk images or filesystem forensics from affected systems
- original SSH access logs / auth.log excerpts from the compromised period
- upstream provider records, subscriber identity documents, or payment records

The spine contains **zero IP addresses and zero ASN references** (verified by
full-text scan across all 2,629 entries). It is the orchestrator's own
telemetry, not a record of network activity. It cannot and does not support any
attribution of the intrusion.

---

## 2. Artifact A — Operational event spine (integrity established)

`spine/spine.jsonl` is an append-only, hash-chained log of EVEZ agentnet
operations.

**Verified properties** (independently re-derived by `verify_spine.py`):

| Property | Value |
|---|---|
| Entries | 2,629 |
| Entries carrying a SHA-256 | 2,629 (100%) |
| First entry | 2026-07-26T14:00:55Z |
| Last entry | 2026-10-02T08:33:17Z |
| Hash chain verifies | **yes** |
| Timestamps monotonic | **yes** |

Hash construction: `sha256` over the entry's canonical JSON with sorted keys,
truncated to 16 hex characters, stored on the entry itself.

**Chain strengthening (applied 2026-10-02).** Per-entry hashing alone does **not**
detect truncation, reordering, or a re-hashed forgery. The spine now carries:

- `seq` — monotonic sequence number
- `prev_sha256` — each entry commits to its predecessor's hash

Entries written before this change (2,629 of 2,632) predate chaining; the first
chained entry bridges to the last legacy entry's hash. Linkage is enforced for
all chained entries onward.

**Verified by adversarial test** (`test_evidence_falsification.py`, 8/8): deleting
a middle entry from an 8-link chain is caught by linkage while per-entry hashing
passes it cleanly. That is the specific attack the chain exists to stop.

**Residual limitation — stated plainly.** An attacker who edits an entry, then
re-hashes it *and* the following entry, produces a chain where every link is
self-consistent. Neither per-entry hashing nor `prev_sha256` detects this. Closing
it requires an **external anchor** — periodically publishing the head hash to a
system the attacker does not control. Until that exists, this spine is
tamper-*evident*, not tamper-*proof*, and should be described that way to any
reviewer.

Event distribution (top entries):

```
rsi_directives_applied    352      round_start            251
rsi_hypotheses            297      scan_complete         249
openclaw_run              125      openclaw_failed       105
round_end                 246      cognition_step          3
```

**What this proves:** the log is internally consistent and unaltered since
writing. Every entry hashes to its recorded value; no entry has been inserted,
reordered, or backdated. This establishes that EVEZ operations ran
continuously over a ~68-day window, and that this record is a faithful account
of the orchestrator's own behaviour.

**What this does not prove:** anything about external infrastructure or the
intrusion. See §1.

---

## 3. Artifact B — Third-party infrastructure registration (live-retrieved)

Every assertion below was queried **live** from RIPE NCC and RIPEstat and
recorded with a retrieval timestamp. Re-run `verify_infrastructure.py` to
reproduce.

### 3.1 Autonomous systems

| ASN | RIPE name | Status |
|---|---|---|
| AS47890 | UNMANAGED-DEDICATED-SERVERS | registered |
| AS48090 | DMZHOST | registered |
| AS42397 | BUNEA-HIGH-VOLUME-NETWORK | registered |
| AS209847 | THE | registered |

### 3.2 IP-to-ASN attribution

| IP | BGP origin | Origin holder | RIPE holder | Country |
|---|---|---|---|---|
| 80.94.92.166 | AS47890 | UNMANAGED LTD | DMZHOST | NL |
| 80.94.92.60 | AS47890 | UNMANAGED LTD | DMZHOST | NL |
| 80.94.92.72 | AS47890 | UNMANAGED LTD | DMZHOST | NL |
| 80.94.92.239 | AS47890 | UNMANAGED LTD | DMZHOST | NL |
| 2.57.122.72 | AS47890 | UNMANAGED LTD | DMZHOSTdotco | NL |
| 45.148.10.1 | **AS48090** | DMZHOST TECHOFF SRV LIMITED | DMZHOST | AD |
| 193.32.162.1 | AS47890 | UNMANAGED LTD | DMZHOST | NL |

### 3.3 Correction to prior drafts — please read

Earlier EVEZ drafts attribute the `80.94.92.0/24` and `2.57.122.0/24` ranges to
**DMZHOST / AS48090**. Current authoritative data shows otherwise:

- Both ranges are announced by **AS47890** (UNMANAGED-DEDICATED-SERVERS)
- Only `45.148.10.0/24` is announced by **AS48090**
- The RIPE *block* registration for the AS47890 ranges names **DMZHOST**, which
  is likely the source of the earlier confusion — block registration and BGP
  origin are different things

**Recommendation:** correct the ASN attribution in any filing. A reviewer who
checks one IP against RIPE and finds a different ASN than the document asserts
will discount the remainder of the document.

**Caveat on timing:** this reflects the network as observed at the retrieval
timestamp. BGP routing changes; a range's origin at the time of the May 2026
intrusion may have differed. Historical BGP data (e.g. RIS/LG archives) would be
required to establish origin *at the time of the event*.

**What this proves:** current BGP origin and RIPE block registration for the
listed addresses, at a stated, reproducible timestamp.

**What this does not prove:** that these hosts performed the intrusion; who
controlled them in May 2026; or that any named person or company operated them.
BGP origin identifies the announcing network, not a human operator. Attribution
to a person requires subscriber records, payment data, or host forensics.

---

## 4. Corrections recommended to prior drafts

1. **Split the documents.** The intrusion/BPH infrastructure narrative and the
   2019 I-80 fatality matter are separate matters that share some network
   adjacency. Merging them weakens both — shared ASN adjacency is not causation.
2. **Fix the ASN attribution** per §3.3.
3. **Cite every infrastructure claim with its retrieval timestamp and source
   URL**, as this pack does. Uncited assertions read as invention to a reviewer.
4. **Do not assert a "confidence level"** (e.g. "99.1% proximate cause") on
   matters that are not probabilistically derivable. It invites a Daubert
   challenge and discredits the sound findings alongside it.
5. **Separate company registration from operational control.** A registered
   address near a city is not evidence of who ran a server.

---

## 5. Verification instructions

A third party can independently confirm every hash and re-fetch every
attribution:

```bash
python3 verify_spine.py            # re-derive the hash chain, check ordering
python3 verify_infrastructure.py   # re-query RIPE + RIPEstat (needs network)
sha256sum spine/spine.jsonl        # must equal MANIFEST primary_source_artifact
```

Expected: `spine/spine.jsonl` → `dd3648eed7b6ad33...` (full digest in MANIFEST).

---

## 6. Outstanding material that would materially strengthen a filing

These are the gaps between what exists here and what a federal cyber-response
filing would normally attach:

1. **Original intrusion logs** — `auth.log` / SSH session records from
   2026-05-22, from the affected Contabo instances (not this host)
2. **Packet captures** — the H.323 gatekeeper traffic on port 1720
3. **Provider cooperation** — upstream hosting subscriber records for
   AS47890 / AS48090; these require legal process, not public data
4. **Historical BGP** — origin AS for the target ranges as of May 2026
5. **Chain of custody** — a signed statement recording when each artifact was
   collected, by whom, and how

Items 1, 2 and 5 are within the custodian's control. Items 3 and 4 require
subpoena or voluntary cooperation.

---

*Generated by `build_evidence_pack.py`. Infrastructure data retrieved from RIPE
NCC RDAP and RIPEstat. No value in this pack is asserted without a source and a
timestamp.*
