import { createApprovalRequest, requiresHumanApproval } from "@/lib/evez/approval";
import { upsertMemory, writeReceipt } from "@/lib/evez/state";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));

  const market = body?.market || "unknown";
  const symbol = body?.symbol || "unknown";
  const side = body?.side || "unknown";
  const size = body?.size || 0;
  const thesis = body?.thesis || "No thesis provided";
  const actor = body?.actor || "operator";

  const approval = createApprovalRequest({
    kind: "trade_execute",
    risk: "critical",
    actor,
    summary: `Trade proposal for ${symbol}`,
    payload: { market, symbol, side, size, thesis },
  });

  const approvalRequired = requiresHumanApproval("trade_execute", "critical");
  const state = {
    proposalId: approval.id,
    approvalRequired,
    market,
    symbol,
    side,
    size,
    thesis,
    status: "proposed",
    createdAt: new Date().toISOString(),
  };

  upsertMemory(`trade:${approval.id}`, state);
  const receipt = writeReceipt("/trading/propose", "pending_approval", state);

  return Response.json({ ok: true, result: { approval, approvalRequired, receipt, state } });
}
