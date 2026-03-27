import type { ConnectorAdapter, HealthReport, NormalizedRecord } from "../../types/connector";
import type { ConnectorAction } from "../../types/actions";
import type { NormalizedEvent } from "../../types/events";
import type { ConnectorReceipt } from "../../types/receipts";

export class GitHubConnector implements ConnectorAdapter {
  name = "github";

  async health(): Promise<HealthReport> {
    return {
      connector: this.name,
      ok: true,
      latency_ms: 80,
      capabilities: ["ingest_repo_events", "prepare_work", "write_receipt"],
    };
  }

  async ingest(input: unknown): Promise<NormalizedEvent[]> {
    return [
      {
        event_id: `github_${Date.now()}`,
        source: "github",
        object_type: "repository_event",
        object_id: "repo",
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
    return ["ingest_repo_events", "prepare_work", "write_receipt"];
  }

  async normalize(raw: unknown): Promise<NormalizedRecord> {
    return {
      connector: this.name,
      object_type: "repository",
      object_id: "raw",
      payload: typeof raw === "object" && raw ? (raw as Record<string, unknown>) : {},
      timestamp: new Date().toISOString(),
    };
  }
}
