import { createApprovalRequest, requiresHumanApproval, type ApprovalRisk } from "@/lib/evez/approval";
import { upsertMemory, writeReceipt } from "@/lib/evez/state";

export type FinanceProposal = {
  kind: "payment_link_create" | "invoice_prepare" | "customer_create";
  risk: ApprovalRisk;
  actor: string;
  summary: string;
  payload: Record<string, unknown>;
};

export function proposeFinanceAction(input: FinanceProposal) {
  const approvalRequired = requiresHumanApproval(input.kind, input.risk);
  const approval = createApprovalRequest({
    kind: input.kind,
    risk: input.risk,
    actor: input.actor,
    summary: input.summary,
    payload: input.payload,
  });

  const state = {
    proposalId: approval.id,
    approvalRequired,
    ...input,
    timestamp: new Date().toISOString(),
  };

  upsertMemory(`finance:${approval.id}`, state);
  const receipt = writeReceipt(`/finance/${input.kind}`, approvalRequired ? "pending_approval" : "prepared", state);

  return { approvalRequired, approval, receipt, state };
}
