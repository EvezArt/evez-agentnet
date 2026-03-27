import { upsertMemory, writeReceipt, getMemory, getReceipts } from "@/lib/evez/state";

export type EngineIntent = {
  kind: "run" | "assert" | "digest" | "alert" | "research" | "integration";
  lane: "command" | "digest" | "alerts" | "research" | "integrations";
  payload: Record<string, unknown>;
};

export function parseCommandText(text: string): EngineIntent | null {
  const lines = text.split(/\r?\n/).map((v) => v.trim()).filter(Boolean);
  const map = Object.fromEntries(lines.map((line) => {
    const idx = line.indexOf(":");
    if (idx === -1) return [line.toUpperCase(), ""];
    return [line.slice(0, idx).trim().toUpperCase(), line.slice(idx + 1).trim()];
  }));

  if (map.RUN) {
    return {
      kind: "run",
      lane: "command",
      payload: {
        queue: map.RUN,
        concurrency: Number(map.CONCURRENCY || 1),
        max: Number(map.MAX || 1),
      },
    };
  }

  if (map.ASSERT) {
    return {
      kind: "assert",
      lane: "command",
      payload: {
        skill: map.ASSERT,
        window: map.WINDOW || "30s",
        threshold: map.THRESHOLD || "0%",
        goal: map.GOAL || "neutral",
      },
    };
  }

  return null;
}

export function runIntent(intent: EngineIntent) {
  const executionId = crypto.randomUUID();
  const state = {
    executionId,
    kind: intent.kind,
    lane: intent.lane,
    status: "completed",
    payload: intent.payload,
    completedAt: new Date().toISOString(),
  };

  upsertMemory(`execution:${executionId}`, state);
  const receipt = writeReceipt(`/engine/${intent.kind}`, "completed", state);

  return { executionId, intent, state, receipt };
}

export function generateDigest() {
  const memory = getMemory();
  const receipts = getReceipts(10);
  const latest = receipts[0];

  return {
    system: "EVEZ AgentNet",
    memoryCount: memory.length,
    receiptCount: receipts.length,
    latestReceipt: latest || null,
    nextAction: latest ? "Evaluate lane routing and external delivery" : "Await first execution"
  };
}

export function evaluateAutonomy() {
  const digest = generateDigest();
  const shouldDigest = digest.receiptCount > 0;

  return {
    shouldDigest,
    shouldAlert: false,
    shouldResearch: digest.memoryCount === 0,
    digest,
  };
}
