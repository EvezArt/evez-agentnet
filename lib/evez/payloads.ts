export type LaneName = "digest" | "alerts" | "research" | "integrations";

export function buildLanePayload(lane: LaneName, input: {
  score: number;
  reason: string;
  memoryCount: number;
  receiptCount: number;
  latestStatus?: string;
}) {
  const base = {
    lane,
    score: Number(input.score.toFixed(4)),
    reason: input.reason,
    memoryCount: input.memoryCount,
    receiptCount: input.receiptCount,
    latestStatus: input.latestStatus || "unknown",
    generatedAt: new Date().toISOString(),
  };

  switch (lane) {
    case "alerts":
      return {
        ...base,
        template: "[ALERT]",
        channel: "#02-runtime-alerts",
        urgency: input.latestStatus === "failed" ? "critical" : "elevated",
        title: "Runtime integrity degraded",
        body: `System status is ${input.latestStatus || "unknown"}. Alert lane preempted because execution health is degraded or ambiguous.`,
      };
    case "digest":
      return {
        ...base,
        template: "[DIGEST]",
        channel: "#evez-autonomous-core",
        title: "Runtime summary",
        body: `Memory count ${input.memoryCount}; receipt count ${input.receiptCount}. Digest lane selected because execution history has accumulated enough signal to justify compression.`,
      };
    case "research":
      return {
        ...base,
        template: "[RESEARCH]",
        channel: "#04-research",
        title: "Doctrine gap detected",
        body: `Research lane selected because memory density is still low relative to runtime ambition. The system is signaling a need for deeper doctrine, benchmarks, or architecture notes.`,
      };
    case "integrations":
      return {
        ...base,
        template: "[INTEGRATION]",
        channel: "#08-integrations",
        title: "Machine chatter segregation",
        body: `Integrations lane selected because runtime activity suggests that machine exhaust or infrastructure metadata should be isolated from digest surfaces.`,
      };
  }
}
