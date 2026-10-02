"""Test the MoE router against the real installed roster.

Key property: routing must never invent an expert. If Ollama is unreachable
the router must report failure, not silently return the biggest model as if
routing had worked.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path("/root/evez-agentnet")
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location("moe", REPO / "moe_router.py")
M = importlib.util.module_from_spec(spec)
sys.modules["moe"] = M
spec.loader.exec_module(M)

results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


print("roster is real, not aspirational")
experts = M.installed_experts()
print(f"  discovered {len(experts)} experts")
expect("Ollama reachable", bool(experts), "no experts discovered")
if experts:
    for n, e in sorted(experts.items()):
        print(f"    {n:28} {e.params:>10}  {e.size_bytes//1048576:>5}MB")

print("\npreferences only reference installed models")
for kind, prefs in M.PREFERENCES.items():
    if not prefs:
        continue
    missing = [p for p in prefs if p not in experts]
    expect(f"{kind}: all preferred experts installed",
           not missing, f"missing={missing}")

print("\ndeterministic routing picks the cheapest adequate expert")
cases = [
    ("def fib(n):\n    return n if n<2 else fib(n-1)+fib(n-2)", "code"),
    ("classify this: the deploy failed twice and customers see 500s", "classify"),
    ("Summarise this incident report in three bullets", "summarise"),
    ("Extract the email address and phone number from: a@b.com 555-0100", "extract"),
    ("Why does the router prefer a smaller model when the task is simple?", "reason"),
]
for text, want in cases:
    kind, strength = M.classify_kind(text)
    r = M.deterministic_route(text, experts)
    expect(f"'{want}' classified (got {kind})", kind == want,
           f"strength={strength}")
    expect(f"  routed to an installed expert", r.expert in experts, str(r.expert))
    if want == "classify":
        expect("  chose the smallest model for classification",
               r.expert == "qwen3:0.6b", str(r.expert))

print("\ncost ordering is respected (cheap first)")
if "qwen3:0.6b" in experts and "hermes3:3b" in experts:
    small = experts["qwen3:0.6b"].size_bytes
    large = experts["hermes3:3b"].size_bytes
    expect("0.6b is genuinely smaller than 3.2b", small < large,
           f"{small} vs {large}")

print("\nembedding is never chosen for generation")
r = M.deterministic_route("embed this text into a vector space", experts)
expect("embed task does not route to an embed-only model",
       "nomic" not in (r.expert or ""), str(r.expert))

print("\nunreachable Ollama must fail loudly, not silently succeed")
_real = M.installed_experts
M.installed_experts = lambda *a, **k: {}
r2 = M.route("anything at all")
expect("no experts -> no route", r2.expert is None, str(r2))
expect("gate is 'none'", r2.gate == "none", str(r2))
expect("reason explains why", "ollama" in r2.reason.lower() or "no " in r2.reason.lower(),
       r2.reason)
M.installed_experts = _real

print("\nforcing a kind")
r3 = M.route("irrelevant text", prefer="code")
expect("prefer forces the kind", r3.task_kind == "code", str(r3))
expect("prefer picks an installed expert", r3.expert in experts, str(r3))
expect("forced gate is labelled", r3.gate == "forced", str(r3))

print("\nunknown preference falls back safely")
r4 = M.route("text", prefer="not_a_real_kind")
expect("unknown prefer still returns a real expert", r4.expert in experts, str(r4))

print("\nJEV gate absent -> deterministic tier used")
import os
os.environ.pop("TYPESAFE_API_KEY", None)
r5 = M.route("classify: something broke")
expect("gate is deterministic without a key", r5.gate == "deterministic", str(r5))
expect("still routes somewhere real", r5.expert in experts, str(r5))

print("\nstatus")
s = M.status()
expect("status reports reachable", s["reachable"] is True)
expect("status lists experts", len(s["experts"]) == len(experts), str(len(s["experts"])))
expect("status reports jev gate off", s["jev_gate"] is False)

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
