# `evez-agentnet` integration plan

This scaffold is built to slot into the repo described by the existing README and ORS layer.

## Practical wiring

1. Instantiate `LivingLogicDaemon` inside `orchestrator.py` before the scan-predict-generate-ship loop.
2. Feed scanner outputs into `daemon.step(...)` as structured text summaries.
3. Use `revision.executive_plan.action_mode` to bias the next actor:
   - `watch` → scanner / predictor
   - `evidence_seek` → scanner / provenance spine / verification loop
   - `prepare` → generator draft pass
   - `construct` → generator + shipper staging path
4. Mirror the daemon checkpoint path and lineage hash into the repo's append-only spine.
5. Treat `.state/build_queue.jsonl` as a task queue for generator or code artifact workers.

## Suggested hook points

- `scanner/scan_agent.py`
  - after each scan batch, serialize the top observations into one event string
- `predictor/predict_agent.py`
  - append forecast uncertainty to the event text so the daemon preserves unresolved branches
- `generator/generate_agent.py`
  - consume `.state/build_queue.jsonl` and materialize drafts
- `shipper/ship_agent.py`
  - only ship when the active identity is `builder` and unresolved count is below your threshold
- `spine/spine.py`
  - append the daemon lineage hash next to the existing provenance record

## Minimal pseudo-hook

```python
store = CheckpointStore(".state")
daemon = LivingLogicDaemon(store)

scan_event = summarize_scan_results(batch)
state = daemon.step(scan_event)

if state["action_mode"] == "evidence_seek":
    run_verification_pass()
elif state["action_mode"] in {"prepare", "construct"}:
    run_generation_pass()
```
