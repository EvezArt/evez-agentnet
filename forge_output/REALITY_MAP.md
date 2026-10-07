# REALITY MAP — GLASS INTERNET x GAME AGENT INFRA
*(ASCII diagram + legend; provenance-tagged. All tags carry SHA-256 root `6691e35`.)*

                +----------------------> [ EDGE / CDN ]
                |                      (DDoS / WAF / rate-limit)
                |                               |
  +-----------+            +---------------+            +-----------+
  |  PLAYERS  |            |   GAME AGENT  |            |  SPECTATOR  |
  +-----------+            +---------------+            +-----------+
               \                  |                      |
                \                 |                      |
                 \                |                      |
                  \               |                      |
                   \              |                      |
      +---------+-----------+------------+-----------+-----------+
      |  PLAYER   |   CLIENT SESSION   |   MATCHMAKING   |  ANTI-CHEAT |
      +-----------+----------------+------------+-------------+
               |                      |                     |
               |                      |                     |
               v                      v                      v
      +-------------------->|==================|================>|  [ AUTH / IDENTITY ]
      |  (credential checks)         |              |              |
      |                      |              |              |
      |                      |              |              |
      |                      |              |              |
      |                      |              |              |
      +-------------------->|==================|================>|  [ DNS / RESOLVERS ]
      |  (WHOIS / RIPE queries)         |              |
      |                      |              |              |
      |                      |              |              |
      +-------------------->|==================|================>|  [ BGP / ROUTING ]
      |  (AS hops / prefix hijack)         |              |
      |                      |              |              |
      |                      |              |              |
      |                      |              |              |
      +-------------------->|==================|================>|  [ ORIGIN / API GW ]
      |  (hosting / registrar)         |              |
      |                      |              |              |
      |                      |              |              |
      +-------------------->|==================|================>|  [ DMZHOST / BGP SURFACE ]
      |  (attacker ranges / SBL-listed)         |
      |                      |              |              |
      |                      |              |              |
      +-------------------->|==================|================>|  [ FIREWALL / OBSERVABILITY TAP ]
      |  (SBL636050 / SBL682858 / SBL678435)   |
      |                      |              |              |
      |                      |              |              |
      +-------------------->|==================|================>|  [ FSC ENGINE ]
      |  (controlled reduction / CS / PS / Ω)     |
      |                                              |
      +--------------------------------------------+    [ AGENT ORCHESTRATOR ]
                                                       (LLM tools; probes; runbooks)
                                                              |
                                                              v
                                                   [ DIAGNOSTICS + ACTIONS ]
                                              (mitigations, compensations, rollbacks)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  [ PERCEPTION ]  ->  mutable views, every signal labeled PENDING/FINAL, provenance-tagged
                     (UI reads projective views; FINAL after finality gate / rebuild)
  [ FINAL ]       ->  the "truth" layer after rebuild; immutable log; every rewrite
                     tagged with provenance (why it changed)
  [ GOVERNANCE ]  ->  { BIAS CONSTITUTION }
                     (target dist + drift bounds + audits)
  [ OBSERVABILITY ] ->  every signal labeled PENDING/FINAL
                     - labeled with provenance (why it changed)
                     - observability taps: OTel logs/metrics/traces

MIXED REALITY COUPLING (the true board):
  Public-layer turbulence (DNS/BGP/TLS/CDN) can masquerade as backend bugs.
  Backend compensations/rollbacks can masquerade as public instability.
  Your job: collapse ambiguity by isolating the layer producing ALL observed reflections.

Nodes referenced in this map (provenance-tagged):
  - 80.94.92.0/22 = SBL682858 (Spamhaus) — full /22 block listed
  - 45.148.10.0/24 = SBL678435 (DMZHOST netname, TECHOFF)
  - 45.156.87.0/24 = SBL688017 (VMHeaven / W heated)
  - 2.57.122.0/24 = SBL636050 (PPTECHNOLOGY / Bunea origin)
  - AS62380 = Bunea Telecom SRL (origin of 2.57.122.0/24)
  - AS47890 = UNMANAGED LTD (Bunea's ASN; origin of 2.57.122.0/24)
  - AS48090 = TECHOFF SRV LIMITED (Palo; attacked 22 May 2026)
  - AS1299 = Arelion (Tier-1; upstream of AS48090)
  - AS174 = Cogent (Tier-1; upstream of AS48090)
  - AS9002 = RETN (Tier-1; upstream of AS48090)
  - AS62380 = Bunea Telecom SRL (originating ASN; tier-1 peer)
  - AS42397 = Bunea Telecom SRL (same as AS62380; origin of 2.57.122.0/24)
  - AS1299 = Arelion (Tier-1; upstream of AS48090)
  - NameCheap (registrar for dmzhost.co; reg. 2015-08-26)
  - GoDaddy (registrar for dmzhost.com)
  - Name.com (registrar for bunea.eu)
  - Cyber_Folks S.R.L. (registrar for banea.ro)
  - Paramount Company Formations LIMITED (ACSP; HMRC-supervised; verified Palo)
  - Spamhaus SBL636050 / SBL636056 / SBL678435 / SBL688017 / SBL682858
