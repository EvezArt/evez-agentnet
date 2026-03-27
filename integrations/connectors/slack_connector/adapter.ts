import type { ConnectorAdapter, HealthReport, NormalizedRecord } from "../../types/connector";
import type { ConnectorAction } from "../../types/actions";
import type { NormalizedEvent } from "../../types/events";
import type { ConnectorReceipt } from "../../types/receipts";

export class SlackConnector implements ConnectorAdapter {
  name = "slack";

  async health(): Promise<HealthReport> {
    return {
      connector: this.name,
      ok: true,
      latency_ms: 50,
      capabilities: ["ingest_messages", "emit_digest", "emit_alert"],
    };
  }

  async ingest(input: unknown): Promise<NormalizedEvent[]> {
    return [
      {
        event_id: `slack_${Date.now()}`,
        source: "slack",
        object_type: "command",
        object_id: "message",
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
        target: action.payload,
      },
    };
  }

  async listCapabilities(): Promise<string[]> {
    return ["ingest_messages", "emit_digest", "emit_alert"];
  }

  async normalize(raw: unknown): Promise<NormalizedRecord> {
    return {
      connector: this.name,
      object_type: "message",
      object_id: "raw",
      payload: typeof raw === "object" && raw ? (raw as Record<string, unknown>) : {},
      timestamp: new Date().toISOString(),
    };
  }
}
