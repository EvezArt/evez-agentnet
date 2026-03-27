export type AuthorityMode = "observe" | "prepare" | "construct" | "ship" | "hold";

export type ConnectorAction = {
  action_id: string;
  target_connector: string;
  action_type: string;
  authority_mode: AuthorityMode;
  payload: Record<string, unknown>;
  causation_id?: string;
  requested_by?: string;
};
