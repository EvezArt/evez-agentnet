import { getMemory, getReceipts, upsertMemory, writeReceipt } from "@/lib/evez/state";
import { scoreLanes } from "@/lib/evez/policy";
import { applyLaneDecay, chooseActiveLanes, getThresholdPolicy } from "@/lib/evez/thresholds";

export function evaluateAutonomyV3() {
  const memory = getMemory();
  const receipts = getReceipts(25);
  const latest = receipts[0];

  const baseScores = scoreLanes({
    memoryCount: memory.length,
    receiptCount: receipts.length,
    latestStatus: latest?.status,
  });

  const normalizedReceipts = receipts.map((receipt: any) => ({
    lane: receipt?.payload?.lane,
    timestamp: receipt?.timestamp,
  }));

  const decayedScores = applyLaneDecay(baseScores, normalizedReceipts);
  const policy = getThresholdPolicy();
  const activeLanes = chooseActiveLanes(decayedScores, policy.threshold, policy.maxActions);

  return {
    policy,
    baseScores,
    decayedScores,
    activeLanes,
    memoryCount: memory.length,
    receiptCount: receipts.length,
  };
}

export function executeLaneSet(decision: ReturnType<typeof evaluateAutonomyV3>) {
  const results = decision.activeLanes.map((laneDecision) => {
    const executionId = crypto.randomUUID();
    const state = {
      executionId,
      lane: laneDecision.lane,
      score: laneDecision.decayedScore ?? laneDecision.score,
      rawScore: laneDecision.score,
      cooldownPenalty: laneDecision.cooldownPenalty ?? 0,
      reason: laneDecision.reason,
      timestamp: new Date().toISOString(),
    };

    upsertMemory(`lane:${executionId}`, state);
    const receipt = writeReceipt(`/engine/lane/${laneDecision.lane}`, "completed", state);

    return { state, receipt };
  });

  return {
    ok: true,
    executed: results.length,
    results,
  };
}
