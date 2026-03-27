export type ReceiptRecord = {
  id: string;
  route: string;
  timestamp: string;
  status: string;
  payload?: unknown;
};

export type MemoryRecord = {
  key: string;
  value: unknown;
  updatedAt: string;
};

const memoryStore = new Map<string, MemoryRecord>();
const receiptStore: ReceiptRecord[] = [];

export function upsertMemory(key: string, value: unknown): MemoryRecord {
  const record: MemoryRecord = { key, value, updatedAt: new Date().toISOString() };
  memoryStore.set(key, record);
  return record;
}

export function getMemory(): MemoryRecord[] {
  return Array.from(memoryStore.values());
}

export function writeReceipt(route: string, status: string, payload?: unknown): ReceiptRecord {
  const record: ReceiptRecord = {
    id: crypto.randomUUID(),
    route,
    timestamp: new Date().toISOString(),
    status,
    payload,
  };
  receiptStore.unshift(record);
  return record;
}

export function getReceipts(limit = 25): ReceiptRecord[] {
  return receiptStore.slice(0, limit);
}
