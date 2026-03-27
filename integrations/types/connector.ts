export type HealthReport = {
  connector: string;
  ok: boolean;
  latency_ms: number;
  capabilities: string[];
  degraded?: boolean;
  notes?: string[];
};

export type NormalizedRecord = {
  connector: string;
  object_type: string;
  object_id: string;
  payload: Record<string, unknown>;
  timestamp: string;
};

export type ConnectorAdapter = {
  name: string;
  health(): Promise<HealthReport>;
  ingest(input: unknown): Promise<import("./events").NormalizedEvent[]>;
  emit(action: import("./actions").ConnectorAction): Promise<import("./receipts").ConnectorReceipt>;
  listCapabilities(): Promise<string[]>;
  normalize(raw: unknown): Promise<NormalizedRecord>;
};
