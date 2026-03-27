import { getMemory, getReceipts, upsertMemory, writeReceipt } from "@/lib/evez/state";
import { scoreLanes } from "@/lib/evez/policy";
import { applyLaneDecay, chooseActiveLanes, getThresholdPolicy } from "@/lib/evez/thresholds";
import { adjustLaneScoresForEscalation } from "@/lib/evez/escalation";
import { buildLanePayload } from "@/lib/evez/payloads";

function countConsecutiveFailures(receipts: any[]) {
  let count = 0;
  for (const receipt of receipts) {
    if (receipt?.status === "failed") count += 1;
    else break;
  }
  return count;
}

export function evaluateAutonomyV4() {
  const memory = getMemory();
  const receipts = getReceipts(25);
  const latest = receipts[0];
  const consecutiveFailures = countConsecutiveFailures(receipts);

  const baseScores = scoreLanes({
    memoryCount: memory.length,
    receiptCount: receipts.length,
    latestStatus: latest?.status,
  });

  const escalatedScores = adjustLaneScoresForEscalation(baseScores, {
    latestStatus: latest?.status,
    consecutiveFailures,
    receiptCount: receipts.length,
    memoryCount: memory.length,
  });

  const normalizedReceipts = receipts.map((receipt: any) => ({
    lane: receipt?.payload?.lane,
    timestamp: receipt?.timestamp,
  }));

  const decayedScores = applyLaneDecay(escalatedScores, normalizedReceipts);
  const policy = getThresholdPolicy();
  const activeLanes = chooseActiveLanes(decayedScores, policy.threshold, policy.maxActions);

  const payloads = activeLanes.map((laneDecision) => buildLanePayload(laneDecision.lane as any, {
    score: laneDecision.decayedScore ?? laneDecision.score,
    reason: laneDecision.reason,
    memoryCount: memory.length,
    receiptCount: receipts.length,
    latestStatus: latest?.status,
  }));

  return {
    policy,
    consecutiveFailures,
    baseScores,
    escalatedScores,
    decayedScores,
    activeLanes,
    payloads,
    memoryCount: memory.length,
    receiptCount: receipts.length,
    latestStatus: latest?.status || "unknown",
  };
}

export function executeLanePayloads(decision: ReturnType<typeof evaluateAutonomyV4>) {
  const results = decision.payloads.map((payload) => {
    const executionId = crypto.randomUUID();
    const state = {
      executionId,
      lane: payload.lane,
      channel: payload.channel,
      template: payload.template,
      payload,
      timestamp: new Date().toISOString(),
    };

    upsertMemory(`payload:${executionId}`, state);
    const receipt = writeReceipt(`/engine/payload/${payload.lane}`, "completed", state);

    return { state, receipt };
  });

  return {
    ok: true,
    executed: results.length,
    results,
  };
}
