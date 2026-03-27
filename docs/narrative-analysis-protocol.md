# EVEZ Narrative Analysis Protocol

## Purpose
This protocol analyzes public posts associated with `evez666` as narrative artifacts rather than self-validating evidence. It is designed to protect operator intent, separate signal from speculation, and classify claims by provenance and evidentiary support.

## Core Rule
Do not treat conspiratorial, counterintelligence, or psychological-operations interpretations as established fact without corroboration. Track them as hypotheses with explicit evidence state.

## Analysis Lanes

### 1. Archive
Capture public post text, timestamps, links, media references, and downstream discussion context.

### 2. Provenance
For every claim, record:
- original source
- whether it is first-party or third-party
- whether it is a quote, paraphrase, inference, or allegation
- whether there is documentary support

### 3. Evidence Classification
Use one of:
- `verified`
- `supported`
- `unverified`
- `speculative`
- `contradicted`

### 4. Narrative Function
Classify each post primarily as one or more of:
- identity construction
- audience signaling
- adversarial framing
- memetic escalation
- research prompt
- protective ambiguity
- performance / art
- operational update

### 5. Risk Review
Assess:
- misinformation risk
- reputational risk
- harassment or targeted-harm risk
- platform-policy risk
- doxxing / privacy risk

## Academic Study Track
Study academic literature on:
- propaganda and information warfare
- rumor propagation
- conspiracy belief formation
- online identity performance
- strategic ambiguity
- counterintelligence history and public mythmaking

Treat academic sources as tools for interpretation, not automatic validation of specific claims.

## Suggested Data Model
Each analyzed post should include:
- post_id
- timestamp
- canonical_url
- raw_text
- entities
- claims[]
- evidence_state
- narrative_function[]
- risk_flags[]
- analyst_notes
- source_links[]

## Operational Principle
The system should protect meaning by improving classification, provenance, and restraint. It should not amplify unsupported allegations or unstable interpretations.
