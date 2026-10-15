import json
from pathlib import Path

from fastapi.testclient import TestClient

from evez_tools import app as module

ADMIN = {"X-EVEZ-Token": "test-admin", "X-EVEZ-Role": "admin"}
AGENT = {"X-EVEZ-Token": "test-agent", "X-EVEZ-Role": "agent"}

def setup_module():
    module.ADMIN_TOKEN = "test-admin"
    module.AGENT_TOKEN = "test-agent"

client = TestClient(module.app)

def valid_manifest(name="echo-tool", endpoint="https://tools.example.org/invoke"):
    return {
        "name": name,
        "version": "1.0.0",
        "description": "Example tool for unit tests",
        "service": {"type": "http", "endpoint": endpoint},
        "input_schema": {"type": "object", "required": ["message"], "additionalProperties": False, "properties": {"message": {"type": "string"}}},
        "output_schema": {"type": "object", "required": ["echo"], "properties": {"echo": {"type": "string"}}},
        "capabilities": ["test.echo"],
        "rate_limit": {"requests_per_minute": 10},
        "auth": {"required": True, "roles": ["agent", "admin"]},
    }

def setup_function():
    module.REGISTRY.clear()
    module.RATE_EVENTS.clear()
    module.READONLY = False
    module.AUDIT_PATH = Path("/tmp/evez-tools-test-audit.jsonl")
    module.AUDIT_PATH.unlink(missing_ok=True)

def test_health_and_auth_required():
    assert client.get("/health").status_code == 200
    assert client.get("/tools").status_code == 401

def test_agent_cannot_register():
    response = client.post("/tools/register", headers=AGENT, json=valid_manifest())
    assert response.status_code == 403

def test_admin_can_register_and_discover_capability():
    response = client.post("/tools/register", headers=ADMIN, json=valid_manifest())
    assert response.status_code == 201
    found = client.get("/tools/capabilities/test.echo", headers=AGENT).json()
    assert found["count"] == 1
    assert found["tools"][0]["name"] == "echo-tool"

def test_registration_rejects_localhost_endpoint():
    response = client.post("/tools/register", headers=ADMIN, json=valid_manifest(endpoint="http://127.0.0.1:8080/run"))
    assert response.status_code == 422

def test_registration_rejects_unknown_fields():
    manifest = valid_manifest()
    manifest["surprise"] = "no"
    response = client.post("/tools/register", headers=ADMIN, json=manifest)
    assert response.status_code == 422

def test_global_readonly_blocks_registry_mutation():
    module.READONLY = True
    response = client.post("/tools/register", headers=ADMIN, json=valid_manifest())
    assert response.status_code == 423

def test_unregister_disables_tool_and_audits_without_raw_params():
    client.post("/tools/register", headers=ADMIN, json=valid_manifest())
    response = client.delete("/tools/echo-tool", headers=ADMIN)
    assert response.status_code == 200
    assert client.get("/tools", headers=AGENT).json()["count"] == 0
    lines = module.AUDIT_PATH.read_text().splitlines()
    assert any(json.loads(line)["event"] == "tool.unregister" for line in lines)
    assert all("test-agent" not in line for line in lines)

def test_invoke_rejects_bad_input_schema_before_network():
    client.post("/tools/register", headers=ADMIN, json=valid_manifest())
    response = client.post("/tools/echo-tool/invoke", headers=AGENT, json={"params": {"unexpected": True}})
    assert response.status_code == 422

def test_replay_events_deterministic_and_rejects_gap():
    events = [{"sequence": 1, "type": "B"}, {"sequence": 0, "type": "A"}]
    assert [e["type"] for e in module.replay_events(events)] == ["A", "B"]
    try:
        module.replay_events([{"sequence": 1, "type": "B"}])
    except ValueError as exc:
        assert "gap" in str(exc)
    else:
        raise AssertionError("expected sequence-gap failure")
