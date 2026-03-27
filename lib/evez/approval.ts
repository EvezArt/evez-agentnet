export type ApprovalRisk = "low" | "medium" | "high" | "critical";

export type ApprovalActionKind =
  | "payment_link_create"
  | "invoice_prepare"
  | "invoice_finalize"
  | "customer_create"
  | "subscription_change"
  | "refund"
  | "trade_proposal"
  | "trade_execute";

export type ApprovalRequest = {
  id: string;
  kind: ApprovalActionKind;
  risk: ApprovalRisk;
  actor: string;
  summary: string;
  payload: Record<string, unknown>;
  createdAt: string;
  approvedAt?: string;
  rejectedAt?: string;
  approver?: string;
  status: "pending" | "approved" | "rejected";
};

const approvalStore = new Map<string, ApprovalRequest>();

export function requiresHumanApproval(kind: ApprovalActionKind, risk: ApprovalRisk) {
  if (kind === "trade_execute") return true;
  if (kind === "refund") return true;
  if (kind === "invoice_finalize") return true;
  if (kind === "subscription_change") return true;
  return risk === "high" || risk === "critical";
}

export function createApprovalRequest(input: Omit<ApprovalRequest, "id" | "createdAt" | "status">) {
  const request: ApprovalRequest = {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    status: "pending",
    ...input,
  };

  approvalStore.set(request.id, request);
  return request;
}

export function approveRequest(id: string, approver: string) {
  const current = approvalStore.get(id);
  if (!current) return null;
  const updated: ApprovalRequest = {
    ...current,
    status: "approved",
    approver,
    approvedAt: new Date().toISOString(),
  };
  approvalStore.set(id, updated);
  return updated;
}

export function rejectRequest(id: string, approver: string) {
  const current = approvalStore.get(id);
  if (!current) return null;
  const updated: ApprovalRequest = {
    ...current,
    status: "rejected",
    approver,
    rejectedAt: new Date().toISOString(),
  };
  approvalStore.set(id, updated);
  return updated;
}

export function listApprovalRequests() {
  return Array.from(approvalStore.values()).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}
