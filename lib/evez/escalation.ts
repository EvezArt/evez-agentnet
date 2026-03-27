export type EscalationInput = {
  latestStatus?: string;
  consecutiveFailures?: number;
  receiptCount: number;
  memoryCount: number;
};

export function computeFailurePressure(input: EscalationInput) {
  const failureBase = input.latestStatus === "failed" ? 0.7 : 0.05;
  const streakPressure = Math.min(0.25, (input.consecutiveFailures || 0) * 0.08);
  const loadPressure = Math.min(0.15, input.receiptCount * 0.02);

  return Math.min(1, failureBase + streakPressure + loadPressure);
}

export function adjustLaneScoresForEscalation(scores: Array<{ lane: string; score: number; reason: string }>, input: EscalationInput) {
  const failurePressure = computeFailurePressure(input);

  return scores.map((entry) => {
    if (entry.lane === "alerts") {
      return {
        ...entry,
        score: Math.min(1, entry.score + failurePressure),
        reason: `${entry.reason} Failure pressure added ${failurePressure.toFixed(2)} to the alert lane because runtime integrity must preempt softer outputs when degradation accumulates.`
      };
    }

    if (entry.lane === "digest" && failurePressure > 0.4) {
      return {
        ...entry,
        score: Math.max(0, entry.score - 0.15),
        reason: `${entry.reason} Digest score was suppressed because alerts should preempt summaries when failure pressure exceeds stability thresholds.`
      };
    }

    return entry;
  }).sort((a, b) => b.score - a.score);
}
