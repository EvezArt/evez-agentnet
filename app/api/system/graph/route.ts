import { getMemory, getReceipts } from "@/lib/evez/state";

export async function GET() {
  return Response.json({
    ok: true,
    system: "EVEZ AgentNet",
    memory: getMemory(),
    receipts: getReceipts(),
    timestamp: new Date().toISOString()
  });
}
