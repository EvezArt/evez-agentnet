# OBLIGATED REASON SYSTEM ◊
## Agent Training & Deployment Kit — v1.0 CANONICAL

**Authored**: EVEZ × SureThing | **Status**: CANONICAL | 2026-02-25

---

## The Problem

Standard LLM behavior:
1. Input arrives
2. Fluent completion that feels complete is generated
3. Confidence ∝ how smooth the output sounds

That is **word prediction dressed as reasoning**.

## The Fix

ORS replaces it with:
1. Input → treated as **conditioned measurement event**
2. Belief state updated over **latent variables and prerequisite gates**
3. Rivals generated, confidence source audited
4. Action chosen by **expected utility under cost**
5. Prediction logged, model calibrated against outcome

Core premise: **A token that arrived is not a token that is true.**

---

## Files

| File | Use | Deploy |
|------|-----|--------|
| `ORS_COMPLETE.md` | Single-file deployment | Paste as system prompt |
| `ORS_system_prompt.md` | Compact system prompt | Paste as system prompt |
| `ORS_formal_spec.md` | Formal spec | Implement / cite from |
| `ORS_training_dataset.md` | SFT/DPO/RLHF dataset | Fine-tuning pipeline |
| `ORS_worksheet.md` | Decision worksheet | Human ops / agent scaffold |

---

## Deployment Paths

**Path A — Immediate** (no training): paste `ORS_system_prompt.md` as system prompt. Immediate behavior change.

**Path B — SFT/DPO**: use `ORS_training_dataset.md`. RIGHT=chosen, WRONG=rejected. Bakes behavior into weights.

**Path C — RLHF**: implement 6 rubric dimensions as automated scorers (0–17 scale). Train reward model. PPO loop.

**Path D — Agent scaffold**: feed `ORS_worksheet.md` sections as CoT template before every output.

---

## Architecture

```
WORLD / LATENT STATES X_t
  → OBSERVATION CHANNELS O_t (sensory | instrumental | social | cognitive events)
  → MEASUREMENT MODEL P(O_t | X_t, M_t)
  → BELIEF STATE BEL_t = P(X_t, R, Θ | O_1:t)
  → EXPLANATION AUDIT (L0→L5, stop rule)
  → EOM P(Y | BEL_t, Action)
  → PREREQUISITE GRAPH (hard/soft gates)
  → DECISION + ACQUISITION ENGINE ACQ* = argmax_k [E[ΔU|ACQ_k] - C(ACQ_k)]
  → ACTION / PROBE / HOLD
  → OUTCOME + CALIBRATION → LOOP
```

---

## Fixed Point

> Treat sensory and cognitive events as noisy, conditioned measurements.
> Update probabilistic beliefs over latent states and prerequisite gates.
> Choose acquisition and action by expected utility under cost.
> Calibrate against outcomes.
> Recurse on explanations only to improve discrimination and contact.

```
Signal ≠ State | Thought ≠ Truth | Confidence ≠ Evidence
Explanation ≠ Replay | Probability ≠ Calibration | Recursion ≠ Rigor | Action ≠ Certainty
```

topology decides. watching it build. ◊