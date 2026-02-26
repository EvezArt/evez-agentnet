# OBLIGATED REASON SYSTEM — Formal Specification v1.0
# Symbol definitions, inference rules, update equations.

## 1. TOKEN CLASSES

### Event Tokens
TH_n=thought | AF_n=affect | UR_n=urge | ME_n=memory | IN_n=insight | MC_n=meta-cog | SO_n=somatic | OBS_n=observation | CE_n=cognitive-event (subclass of OBS)

### Condition Tokens
ST=body/system state | CT=context | AT=attention state | PR=priming

### Confidence Force Channels
EVID=evidence | FLU=fluency | FAM=familiarity | AFW=affect weight | IDF=identity fit | SAL=salience | SOC=social pressure | GOAL=goal alignment

### Claim Tokens
CL_x=candidate claim | RIV_x=rival | DEF_x=defeater | TEST_x=discriminating test

### Probabilistic Variables
X_t=latent state | O_t=observation | M_t=measurement apparatus | R_i=prerequisite | A_t=action | E_t=exogenous disturbance | Y=outcome | Θ=params | BEL_t=belief state

## 2. INFERENCE RULES

R-OCC:   OBS_n ⊢ Occurred(OBS_n)
R-NON:   OBS_n ⊬ True(Content(OBS_n))
R-COND:  (OBS_n, ST, CT, AT) ⊢ Admissible(OBS_n); OBS_n without conditions ⊢ Inadmissible
R-ACQ:   Claim(X observed) requires Declare(source, recency, M_t, known_noise)
R-CONF:  conf(CL_x) ≠ EVID(CL_x) unless conf traced to EVID
R-CONT:  conf_source ∈ {FLU,FAM,AFW,IDF,SAL,SOC,GOAL} ⊢ Contaminated → Downweight → Flag
R-RIV:   Candidate(CL_x) ⊢ Required ∃ RIV_1; no rival ⊢ Flagged(framing_lock)
R-TEST:  conf(CL_x) > τ_strong ⊢ Required TEST_x discriminating CL_x from RIV_j
R-INV:   CL_x survives shift_k ⊢ STABLE gains weight; CL_x fails shift_k ⊢ state-locked
R-COMMIT: STABLE(CL_x) ∧ cost/risk ≤ bounds ⊢ COMMIT(CL_x, p, revision_condition)
R-PHASE: post-COMMIT: confirming amplified; disconfirming filtered; raise DEF priority
R-CALIB: CalibError(EOM) > ε ⊢ REVISE({EOM, Θ, M_t, PG})

## 3. PROOF STATUS LADDER

RAW → TAGGED iff Admissible
    → PLAUSIBLE iff coherent under BEL_t
    → RIVALED iff ∃ RIV_1
    → TESTABLE iff ∃ TEST_x
    → STABLE(local) iff holds in current frame
    → STABLE(cross) iff passes ≥ 4 invariance shifts
    → ACTIONABLE(p) iff P(OUT|ACT_j,BEL_t) ≥ τ_act ∧ Risk ≤ ρ
    → REJECTED / REVISED / MAINTAINED

## 4. PROBABILISTIC EQUATIONS

# Belief update (Bayesian)
BEL_t = P(X_t, R, Θ | O_1:t) ∝ P(O_t | X_t, R, M_t, Θ) · P(X_t, R, Θ | O_1:t-1)

# Transition
P(X_t+1 | X_t, A_t, E_t)

# Expected outcome
P(Y | BEL_t, A_j)

# Hard-gate prerequisite model
P(Y=1) ≈ 0 if any critical R_i = 0
P(Y=1) = P(Y=1 | ∩_i R_i) · P(∩_i R_i)

# Soft-gate (factor graph)
logit P(Y=1) = β_0 + Σ_i β_i R_i + Σ_j γ_j X_j + Σ_k δ_k A_k

# Acquisition utility (VOI)
ACQ* = argmax_k ( E[ΔU | ACQ_k] - C(ACQ_k) )

# Prerequisite acquisition priority
Score(R_i) ≈ ( Impact(R_i→Y) · Uncertainty(R_i) · DecisionSensitivity ) / Cost(acquire R_i)

# Actionability threshold
ACTIONABLE(ACT_j, p) iff:
  P(Y | ACT_j, BEL_t) ≥ τ_act
  ∧ Risk(ACT_j) ≤ ρ
  ∧ ∀ hard-gate R_i: P(R_i=1) > τ_gate

# Accountability clause
CalibError(EOM) > ε ⊢ REVISE({EOM, Θ, M_t, PG})

## 5. UNCERTAINTY TAXONOMY

Aleatoric σ_A: irreducible world variance — model it, don't fight it
Epistemic σ_E: ignorance (missing data, poor model) — acquire; improve model
Measurement σ_M: detector error, noise, threshold, bias — audit M_t; calibrate
Decision σ_D: induced by action/utility assumptions — enumerate; clarify utility

NEVER collapse into single confidence score.

## 6. EXPLANATION STACK (L0–L5)

L0 Claim/Event:       What exactly happened?
L1 Mechanism:         How did this happen?
L2 Model-of-model:    Why these categories/terms?
L3 Framing incentives: Why this explanatory style for this audience?
L4 Explanity production: Why does this feel inevitable/airtight?
L5 Stop rule:         What test/action threshold ends recursion?

Recurse(Lk → Lk+1) iff improves {discrimination, test_selection, calibration, action_quality}
Otherwise: STOP. Depth ≠ rigor.

## 7. COGNITIVE EVENT LIKELIHOOD MODEL

P(CE_t = fear_spike | X_t, ST_t, PR_t)  ← valid
fear_spike ⊢ danger                      ← INVALID SHORTCUT

Cognitive events are observation channels about latent states, not direct state readouts.

## 8. FIXED-POINT THEOREM

Given:
1. Observations are filtered, state-dependent, thresholded measurements of latent states
2. Confidence can arise from non-evidential force channels
3. Commitment changes evidence intake
4. Prerequisites gate outcome probability
5. Models are scoreable against outcomes

Then reason cannot be obedience to inner appearance.

It must be: resource-bounded probabilistic state estimation over latent variables
and prerequisite gates, coupled to calibrated expected-outcome models and
value-of-information-guided acquisition, with provisional commitment
under explicit revision conditions.

Corollary 1 (Recursion bound): Recursion terminates when discrimination no longer improves.
Corollary 2 (Meta-immunity impossibility): Self-observation is itself a cognitive event subject to all the same rules.