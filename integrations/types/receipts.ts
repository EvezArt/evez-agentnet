export type ConnectorReceipt = {
  receipt_id: string;
  connector: string;
  action_type: string;
  status: "accepted" | "rejected" | "deferred" | "failed";
  timestamp: string;
  commit_hash?: string;
  lineage_hash?: string;
  details?: Record<string, unknown>;
};
