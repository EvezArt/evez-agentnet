import { approveRequest, rejectRequest, listApprovalRequests } from "@/lib/evez/approval";

export async function GET() {
  return Response.json({ ok: true, approvals: listApprovalRequests() });
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const id = body?.id;
  const approver = body?.approver || "operator";
  const decision = body?.decision;

  if (!id || !decision) {
    return Response.json({ ok: false, error: "Missing id or decision" }, { status: 400 });
  }

  const result = decision === "approve"
    ? approveRequest(id, approver)
    : rejectRequest(id, approver);

  if (!result) {
    return Response.json({ ok: false, error: "Approval request not found" }, { status: 404 });
  }

  return Response.json({ ok: true, result });
}
