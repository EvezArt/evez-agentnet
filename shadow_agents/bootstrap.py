from access_layers.evez_access_layer import access_layer
from shadow_agents.phi_drift_predictor import PhiDriftPredictor
from shadow_agents.emergence_validator import EmergenceValidator
from shadow_agents.hash_auditor import HashAuditor

phi_agent = PhiDriftPredictor()
emerge_agent = EmergenceValidator()
hash_agent = HashAuditor()

access_layer.subscribe(phi_agent.on_event)
access_layer.subscribe(emerge_agent.on_event)
access_layer.subscribe(hash_agent.on_event)

print("[BOOT] Shadow agents online")