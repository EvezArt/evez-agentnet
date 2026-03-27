import type { ConnectorAdapter } from "../types/connector";

export class ConnectorRegistry {
  private connectors = new Map<string, ConnectorAdapter>();

  register(adapter: ConnectorAdapter) {
    this.connectors.set(adapter.name, adapter);
  }

  get(name: string): ConnectorAdapter {
    const adapter = this.connectors.get(name);
    if (!adapter) {
      throw new Error(`connector_not_registered:${name}`);
    }
    return adapter;
  }

  list(): ConnectorAdapter[] {
    return [...this.connectors.values()];
  }
}
