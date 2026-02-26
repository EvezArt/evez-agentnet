# OBLIGATED REASON SYSTEM — Practical Worksheet
# Run in real time against any decision under uncertainty.
# Fill each section. Skip nothing. The gaps are the information.

## WORKSHEET — SINGLE DECISION INSTANCE

**Date/Time:**
**State:** (sleep, stress, hunger, pressure, social stakes)
**Context:** (deadline, audience, stakes, trigger)

---

### S1 — OUTCOME
```
OUT =
Type = [ binary | continuous | time-to-event ]
Success definition =
Failure definition =
Time horizon =
```

### S2 — TRIGGER EVENT
```
Event: [ TH | AF | UR | ME | IN | SO | MC ]
One sentence:
Source = | Recency = | Framing = | Known noise =
```

### S3 — CONFIDENCE SOURCE AUDIT
```
[ ] EVID  [ ] FLU  [ ] FAM  [ ] AFW  [ ] IDF  [ ] SAL  [ ] SOC  [ ] GOAL
Primary channel = | EVID-grounded? [ Y / N ]
If N: contamination noted, confidence downweighted.
```

### S4 — CLAIM
```
CL_1 =
Proof status: [ RAW | TAGGED | PLAUSIBLE | RIVALED | TESTABLE | STABLE-local | STABLE-cross | ACTIONABLE ]
```

### S5 — RIVALS
```
RIV_1 = | RIV_2 = | RIV_3 =
Most threatening rival:
Discriminating test:
```

### S6 — PREREQUISITES
```
PRQ_1 = ____________ [ hard / soft ] P(met) =
PRQ_2 = ____________ [ hard / soft ] P(met) =
PRQ_3 = ____________ [ hard / soft ] P(met) =
PRQ_4 = ____________ [ hard / soft ] P(met) =
PRQ_5 = ____________ [ hard / soft ] P(met) =
Any hard gate P(met) < 0.5? → HOLD until resolved.
Highest uncertainty × impact → acquire first.
```

### S7 — UNCERTAINTY DECOMPOSITION
```
Aleatoric: [ low | medium | high ] Description:
Epistemic:  [ low | medium | high ] Main gaps: | Reducible via:
Measurement: [ low | medium | high ] Channels: | Biases: | State effects:
```

### S8 — BELIEF ESTIMATES
```
P(PRQ_1 met) = | P(PRQ_2 met) = | P(PRQ_3 met) =
P(OUT | ACT_1) = | P(OUT | ACT_2) = | P(OUT | no action) =
```

### S9 — ACQUISITION OPTIONS
```
ACQ_1 = _______ Cost [low|med|high] VOI [low|med|high]
ACQ_2 = _______ Cost [low|med|high] VOI [low|med|high]
ACQ_3 = _______ Cost [low|med|high] VOI [low|med|high]
Best: ACQ___ — changes decision if result is:
YES → | NO →
```

### S10 — INVARIANCE TESTS
```
[ ] Time shift    [ ] State shift   [ ] Frame shift
[ ] Audience shift [ ] Goal shift   [ ] Identity shift  [ ] Evidence shift
Passed: ___ / 7
If < 4: state-locked artifact. Do not commit.
```

### S11 — ACTION THRESHOLD
```
Act if ALL:
  [ ] P(OUT | ACT_j) ≥ _____
  [ ] Risk ≤ _____
  [ ] No hard-gate P(met) < 0.5
  [ ] ≥1 invariance test passes

Status: [ ACTIONABLE | HOLD | ACQUIRE MORE | REJECT ]
Commitment: [ provisional | moderate | strong ]
Revise if:
```

### S12 — CALIBRATION LOG (fill after outcome)
```
Predicted: P(OUT) = | Actual: [ success | failure | partial ]
Which prerequisites failed:
Assumed met but wasn't:
Detector conditions:
Main error: [ wrong model | missing gate | measurement error | aleatoric ]
Model update:
```

---

## MINIMAL 60-SECOND VERSION
1. What exactly happened? (event, not verdict)
2. What state am I in?
3. What's making this feel true? (EVID or contamination?)
4. One rival interpretation.
5. One critical gate not yet checked.
6. Cheapest thing to check right now.
7. Commit provisionally — or hold.

## MNEMONIC
```
OBSERVE → CONDITION → RIVAL → MODEL → GATE → ACQUIRE → ACT → CALIBRATE
Signal ≠ State | Thought ≠ Truth | Confidence ≠ Evidence
Explanation ≠ Replay | Probability ≠ Calibration | Recursion ≠ Rigor | Action ≠ Certainty
```