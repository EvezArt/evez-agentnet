import type { ConnectorAdapter, HealthReport, NormalizedRecord } from "../../types/connector";
import type { ConnectorAction } from "../../types/actions";
import type { NormalizedEvent } from "../../types/events";
import type { ConnectorReceipt } from "../../types/receipts";

export class VercelConnector implements ConnectorAdapter {
  name = "vercel";

  async health(): Promise<HealthReport> {
    return {
      connector: this.name,
      ok: true,
      latency_ms: 60,
      capabilities: ["ingest_deployment_events", "emit_runtime_receipt", "prepare_deploy"],
    };
  }

  async ingest(input: unknown): Promise<NormalizedEvent[]> {
    return [
      {
        event_id: `vercel_${Date.now()}`,
        source: "vercel",
        object_type: "deployment_event",
        object_id: "deployment",
        timestamp: new Date().toISOString(),
        payload: typeof input === "object" && input ? (input as Record<string, unknown>) : {},
      },
    ];
  }

  async emit(action: ConnectorAction): Promise<ConnectorReceipt> {
    return {
      receipt_id: `rcpt_${Date.now()}`,
      connector: this.name,
      action_type: action.action_type,
      status: "accepted",
      timestamp: new Date().toISOString(),
      details: {
        authority_mode: action.authority_mode,
        payload: action.payload,
      },
    };
  }

  async listCapabilities(): Promise<string[]> {
    return ["ingest_deployment_events", "emit_runtime_receipt", "prepare_deploy"];
  }

  async normalize(raw: unknown): Promise<NormalizedRecord> {
    return {
      connector: this.name,
      object_type: "deployment",
      object_id: "raw",
      payload: typeof raw === "object" && raw ? (raw as Record<string, unknown>) : {},
      timestamp: new Date().toISOString(),
    };
  }
}
