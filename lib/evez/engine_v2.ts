import { getMemory, getReceipts, upsertMemory, writeReceipt } from "@/lib/evez/state";
import { scoreLanes, choosePrimaryLane } from "@/lib/evez/policy";

export function evaluateAutonomyV2() {
  const memory = getMemory();
  const receipts = getReceipts(10);
  const latest = receipts[0];

  const scores = scoreLanes({
    memoryCount: memory.length,
    receiptCount: receipts.length,
    latestStatus: latest?.status,
  });

  const primary = choosePrimaryLane(scores);

  return {
    scores,
    primary,
    memoryCount: memory.length,
    receiptCount: receipts.length,
  };
}

export function executeLaneDecision(decision: ReturnType<typeof evaluateAutonomyV2>) {
  if (!decision.primary) return { ok: false };

  const executionId = crypto.randomUUID();

  const state = {
    executionId,
    lane: decision.primary.lane,
    score: decision.primary.score,
    reason: decision.primary.reason,
    timestamp: new Date().toISOString(),
  };

  upsertMemory(`lane:${executionId}`, state);
  const receipt = writeReceipt(`/engine/lane/${decision.primary.lane}`, "completed", state);

  return { ok: true, state, receipt };
}
