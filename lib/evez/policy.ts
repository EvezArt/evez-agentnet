export type LaneScore = {
  lane: "digest" | "alerts" | "research" | "integrations";
  score: number;
  reason: string;
};

export function scoreLanes(input: {
  memoryCount: number;
  receiptCount: number;
  latestStatus?: string;
}) : LaneScore[] {
  const { memoryCount, receiptCount, latestStatus } = input;

  const scores: LaneScore[] = [
    {
      lane: "digest",
      score: receiptCount > 0 ? Math.min(1, 0.35 + receiptCount * 0.1) : 0.05,
      reason: "Digest score rises when receipts accumulate because runtime summaries become more valuable as execution history grows."
    },
    {
      lane: "alerts",
      score: latestStatus === "failed" ? 0.95 : 0.08,
      reason: "Alert score spikes only on explicit failure state so the interrupt lane stays high-signal and does not degrade into noise."
    },
    {
      lane: "research",
      score: memoryCount < 3 ? 0.6 : 0.15,
      reason: "Research score rises when memory is sparse because doctrinal and contextual gaps should be filled before more execution complexity is added."
    },
    {
      lane: "integrations",
      score: receiptCount > 5 ? 0.4 : 0.1,
      reason: "Integrations score rises modestly with higher activity because more machine chatter and plumbing metadata are likely to require segregation."
    }
  ];

  return scores.sort((a, b) => b.score - a.score);
}

export function choosePrimaryLane(scores: LaneScore[]) {
  return scores[0] ?? null;
}
