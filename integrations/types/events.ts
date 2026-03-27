export type NormalizedEvent = {
  event_id: string;
  source: string;
  object_type: string;
  object_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
  lineage_hash?: string;
  causation_id?: string;
};
