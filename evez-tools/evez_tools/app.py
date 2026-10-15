"""A minimal hardened reference API for registering and invoking mesh tools.

This is a single-process reference implementation. Production multi-node use
must put the registry behind an authenticated gateway and replace in-memory
state with a durable, consensus-aware store.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
import urllib.parse
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field, ConfigDict

APP_NAME = "EVEZ Distributed Tool Registry"
READONLY = os.getenv("EVEZ_TOOLS_READONLY", "0").lower() in {"1", "true", "yes", "on"}
ADMIN_TOKEN = os.getenv("EVEZ_ADMIN_TOKEN", "")
AGENT_TOKEN = os.getenv("EVEZ_AGENT_TOKEN", "")
AUDIT_PATH = Path(os.getenv("EVEZ_AUDIT_PATH", "logs/audit.jsonl"))
REGISTRY: dict[str, dict[str, Any]] = {}
RATE_EVENTS: dict[str, deque[float]] = defaultdict(deque)

app = FastAPI(title=APP_NAME, version="1.0.0")

class ToolService(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["http", "grpc"]
    endpoint: str = Field(min_length=8, max_length=2048)

class RateLimit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requests_per_minute: int = Field(default=60, ge=1, le=10000)

class AuthPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    required: bool = True
    roles: list[Literal["agent", "admin"]] = Field(default_factory=lambda: ["agent", "admin"], min_length=1)

class ToolManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(pattern=r"^[a-z][a-z0-9-]{1,62}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
    description: str = Field(min_length=1, max_length=500)
    service: ToolService
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    capabilities: list[str] = Field(min_length=1, max_length=64)
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    auth: AuthPolicy = Field(default_factory=AuthPolicy)
    enabled: bool = True

class InvokeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    params: dict[str, Any]
    timeout_seconds: int = Field(default=20, ge=1, le=120)
    idempotency_key: str | None = Field(default=None, max_length=200)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def audit(event: dict[str, Any]) -> None:
    """Append redacted metadata; never serialize raw input values or secrets."""
    record = {"timestamp": utc_now(), **event}
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    except OSError:
        # Fail closed for writes/invocations if the audit sink is unavailable.
        raise HTTPException(status_code=503, detail="Audit sink unavailable; request not performed")


def body_digest(data: Any) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def caller(x_evez_token: str | None = Header(default=None), x_evez_role: str | None = Header(default=None)) -> dict[str, str]:
    # Explicit token values are required; empty defaults are never valid credentials.
    if not x_evez_token or not x_evez_role:
        raise HTTPException(status_code=401, detail="Missing EVEZ credentials")
    if x_evez_role == "admin" and ADMIN_TOKEN and hmac.compare_digest(x_evez_token, ADMIN_TOKEN):
        return {"role": "admin", "identity": "admin-token"}
    if x_evez_role == "agent" and AGENT_TOKEN and hmac.compare_digest(x_evez_token, AGENT_TOKEN):
        return {"role": "agent", "identity": "agent-token"}
    raise HTTPException(status_code=403, detail="Invalid credentials or role")


def admin_only(who: dict[str, str] = Depends(caller)) -> dict[str, str]:
    if who["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return who


def safe_endpoint(raw: str, service_type: str) -> str:
    parsed = urllib.parse.urlsplit(raw)
    expected = {"http": {"http", "https"}, "grpc": {"grpc", "grpcs"}}[service_type]
    if parsed.scheme not in expected or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Endpoint scheme does not match service type")
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0", "169.254.169.254"}:
        raise HTTPException(status_code=422, detail="Local and link-local endpoints are blocked by default")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="Credentials must not be embedded in endpoint URLs")
    return raw


def validate_schemas(manifest: ToolManifest) -> None:
    try:
        Draft202012Validator.check_schema(manifest.input_schema)
        Draft202012Validator.check_schema(manifest.output_schema)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON Schema: {type(exc).__name__}") from exc


def rate_check(name: str, limit: int) -> None:
    now = time.monotonic()
    events = RATE_EVENTS[name]
    while events and now - events[0] >= 60:
        events.popleft()
    if len(events) >= limit:
        raise HTTPException(status_code=429, detail="Tool rate limit exceeded")
    events.append(now)


def public_tool(item: dict[str, Any]) -> dict[str, Any]:
    # Do not leak private auth tokens; only publish declared policy and schema.
    return {k: v for k, v in item.items() if k not in {"manifest_digest", "registered_by"}}

@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "healthy", "service": APP_NAME, "version": "1.0.0", "readonly": READONLY, "registered_tools": len(REGISTRY)}

@app.get("/tools")
def list_tools(capability: str | None = None, include_disabled: bool = False, who: dict[str, str] = Depends(caller)) -> dict[str, Any]:
    values = []
    for item in REGISTRY.values():
        if not include_disabled and not item["enabled"]:
            continue
        if capability and capability not in item["capabilities"]:
            continue
        values.append(public_tool(item))
    return {"tools": values, "count": len(values)}

@app.get("/tools/capabilities/{capability:path}")
def tools_by_capability(capability: str, who: dict[str, str] = Depends(caller)) -> dict[str, Any]:
    matches = [public_tool(t) for t in REGISTRY.values() if t["enabled"] and capability in t["capabilities"]]
    return {"capability": capability, "tools": matches, "count": len(matches)}

@app.get("/tools/{name}/health")
def tool_health(name: str, who: dict[str, str] = Depends(caller)) -> dict[str, Any]:
    item = REGISTRY.get(name)
    if not item:
        raise HTTPException(status_code=404, detail="Unknown tool")
    return {"name": name, "status": "registered" if item["enabled"] else "disabled", "version": item["version"], "endpoint_configured": bool(item["service"].get("endpoint"))}

@app.get("/tools/{name}")
def get_tool(name: str, who: dict[str, str] = Depends(caller)) -> dict[str, Any]:
    item = REGISTRY.get(name)
    if not item:
        raise HTTPException(status_code=404, detail="Unknown tool")
    return public_tool(item)

@app.post("/tools/register", status_code=201)
def register_tool(manifest: ToolManifest, who: dict[str, str] = Depends(admin_only)) -> dict[str, Any]:
    if READONLY:
        raise HTTPException(status_code=423, detail="EVEZ_TOOLS_READONLY is enabled")
    safe_endpoint(manifest.service.endpoint, manifest.service.type)
    validate_schemas(manifest)
    previous = REGISTRY.get(manifest.name)
    if previous and previous["version"] == manifest.version and previous["manifest_digest"] != body_digest(manifest.model_dump(mode="json")):
        raise HTTPException(status_code=409, detail="Same name/version cannot be re-registered with different content")
    item = manifest.model_dump(mode="json")
    item["manifest_digest"] = body_digest(item)
    item["registered_by"] = who["identity"]
    audit({"event": "tool.register", "actor": who["identity"], "role": who["role"], "tool": manifest.name, "version": manifest.version, "manifest_digest": item["manifest_digest"]})
    REGISTRY[manifest.name] = item
    return {"registered": True, "tool": public_tool(item), "manifest_digest": item["manifest_digest"]}

@app.delete("/tools/{name}")
def unregister_tool(name: str, who: dict[str, str] = Depends(admin_only)) -> dict[str, Any]:
    if READONLY:
        raise HTTPException(status_code=423, detail="EVEZ_TOOLS_READONLY is enabled")
    item = REGISTRY.get(name)
    if not item:
        raise HTTPException(status_code=404, detail="Unknown tool")
    audit({"event": "tool.unregister", "actor": who["identity"], "role": who["role"], "tool": name, "version": item["version"], "manifest_digest": item["manifest_digest"]})
    # Tombstone rather than silently removing; preserves evidence of administrative action.
    item["enabled"] = False
    return {"unregistered": True, "name": name, "status": "disabled"}

@app.post("/tools/{name}/invoke")
async def invoke_tool(name: str, body: InvokeParams, who: dict[str, str] = Depends(caller)) -> dict[str, Any]:
    item = REGISTRY.get(name)
    request_id = secrets.token_hex(12)
    if not item or not item["enabled"]:
        audit({"event": "tool.invoke.denied", "request_id": request_id, "actor": who["identity"], "tool": name, "reason": "unknown_or_disabled"})
        raise HTTPException(status_code=404, detail="Tool unavailable")
    if who["role"] not in item["auth"]["roles"]:
        audit({"event": "tool.invoke.denied", "request_id": request_id, "actor": who["identity"], "tool": name, "reason": "role_denied"})
        raise HTTPException(status_code=403, detail="Caller role is not allowed for this tool")
    if READONLY:
        # Invocation is not assumed read-only, so global readonly blocks all invocations.
        audit({"event": "tool.invoke.denied", "request_id": request_id, "actor": who["identity"], "tool": name, "reason": "readonly_mode"})
        raise HTTPException(status_code=423, detail="EVEZ_TOOLS_READONLY blocks invocation")
    errors = sorted(Draft202012Validator(item["input_schema"]).iter_errors(body.params), key=lambda e: list(e.path))
    if errors:
        raise HTTPException(status_code=422, detail={"message": "Input schema validation failed", "errors": [e.message for e in errors[:10]]})
    rate_check(name, item["rate_limit"]["requests_per_minute"])
    target = safe_endpoint(item["service"]["endpoint"], item["service"]["type"])
    if item["service"]["type"] != "http":
        raise HTTPException(status_code=501, detail="gRPC transport adapter is not bundled in this reference server")
    # Audit successful intent before dispatch; no raw params are recorded.
    audit({"event": "tool.invoke.started", "request_id": request_id, "actor": who["identity"], "role": who["role"], "tool": name, "version": item["version"], "manifest_digest": item["manifest_digest"], "params_sha256": body_digest(body.params)})
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=body.timeout_seconds, follow_redirects=False, trust_env=False) as client:
            upstream = await client.post(target, json=body.params, headers={"X-EVEZ-Request-ID": request_id})
        upstream.raise_for_status()
        result = upstream.json()
        output_errors = sorted(Draft202012Validator(item["output_schema"]).iter_errors(result), key=lambda e: list(e.path))
        if output_errors:
            raise ValueError("Upstream output schema validation failed")
    except httpx.TimeoutException:
        audit({"event": "tool.invoke.failed", "request_id": request_id, "actor": who["identity"], "tool": name, "reason": "timeout"})
        raise HTTPException(status_code=504, detail={"message": "Tool timed out", "request_id": request_id})
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        audit({"event": "tool.invoke.failed", "request_id": request_id, "actor": who["identity"], "tool": name, "reason": type(exc).__name__})
        raise HTTPException(status_code=502, detail={"message": "Tool invocation or result validation failed", "request_id": request_id}) from exc
    duration_ms = int((time.monotonic() - started) * 1000)
    audit({"event": "tool.invoke.succeeded", "request_id": request_id, "actor": who["identity"], "tool": name, "version": item["version"], "duration_ms": duration_ms, "result_sha256": body_digest(result)})
    return {"request_id": request_id, "tool": name, "version": item["version"], "duration_ms": duration_ms, "result": result}

# A deliberately small local utility for deterministic state ledger alignment.
def replay_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a deterministic copy sorted by sequence, rejecting gaps/duplicates."""
    seen: set[int] = set()
    ordered = sorted(events, key=lambda event: event.get("sequence", -1))
    expected = 0
    for event in ordered:
        seq = event.get("sequence")
        if not isinstance(seq, int) or seq < 0 or seq in seen:
            raise ValueError("Invalid or duplicate event sequence")
        if seq != expected:
            raise ValueError(f"Event sequence gap: expected {expected}, got {seq}")
        seen.add(seq)
        expected += 1
    return ordered
