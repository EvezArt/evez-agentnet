import { ConnectorRegistry } from "../registry/connector_registry";
import type { ConnectorAction } from "../types/actions";
import type { NormalizedEvent } from "../types/events";
import type { ConnectorReceipt } from "../types/receipts";

export class IntegrationGovernor {
  constructor(private registry: ConnectorRegistry) {}

  async pollHealth() {
    return Promise.all(this.registry.list().map((connector) => connector.health()));
  }

  async ingest(source: string, raw: unknown): Promise<NormalizedEvent[]> {
    const connector = this.registry.get(source);
    const events = await connector.ingest(raw);
    for (const event of events) {
      await this.writeToSpine(event);
    }
    return events;
  }

  async dispatch(actions: ConnectorAction[]): Promise<ConnectorReceipt[]> {
    const receipts: ConnectorReceipt[] = [];
    for (const action of actions) {
      const connector = this.registry.get(action.target_connector);
      const receipt = await connector.emit(action);
      receipts.push(receipt);
      await this.writeReceipt(receipt);
      await this.updateProofSurface(receipt);
    }
    return receipts;
  }

  private async writeToSpine(event: NormalizedEvent) {
    console.log("SPINE_EVENT", JSON.stringify(event));
  }

  private async writeReceipt(receipt: ConnectorReceipt) {
    console.log("CONNECTOR_RECEIPT", JSON.stringify(receipt));
  }

  private async updateProofSurface(receipt: ConnectorReceipt) {
    console.log("PROOF_UPDATE", JSON.stringify(receipt));
  }
}
