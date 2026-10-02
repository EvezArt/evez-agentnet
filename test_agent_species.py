"""Test species-to-agent binding and — critically — that the bounds actually
constrain behaviour rather than decorating it.

The whole failure mode this repo keeps hitting is a declarative surface: a
mapping documented in AGENTNET_INTEGRATION.md that nothing enforces. These
assert may_publish() actually denies a low-tau species.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

REPO = Path("/root/evez-agentnet")
sys.path.insert(0, str(REPO))

import cryptozoo as CZ            # noqa: E402
import agent_species as AS        # noqa: E402

AS.ASSIGNMENT_PATH = Path(tempfile.mkdtemp()) / "agent_species.json"

results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


print("phase mapping matches the spec table")
expect("observe -> NOCTIS/ABYSSAL", AS.PHASE_SPECIES["observe"] == ["NOCTIS", "ABYSSAL"])
expect("orient -> AURIX/VERDANT", AS.PHASE_SPECIES["orient"] == ["AURIX", "VERDANT"])
expect("decide -> FRACTOS/IGNIS", AS.PHASE_SPECIES["decide"] == ["FRACTOS", "IGNIS"])
expect("act -> SYNTHEX/LUMARA", AS.PHASE_SPECIES["act"] == ["SYNTHEX", "LUMARA"])
expect("pipeline HARVEST->NOCTIS", AS.PIPELINE_SPECIES["HARVEST"] == "NOCTIS")
expect("pipeline SCOUT->AURIX", AS.PIPELINE_SPECIES["SCOUT"] == "AURIX")
expect("pipeline WITNESS->VERDANT", AS.PIPELINE_SPECIES["WITNESS"] == "VERDANT")
expect("pipeline DEPLOY->SYNTHEX", AS.PIPELINE_SPECIES["DEPLOY"] == "SYNTHEX")

print("\nassigned species must exist in the registry")
for phase in AS.PHASE_SPECIES:
    for sp in AS.PHASE_SPECIES[phase]:
        expect(f"{phase}/{sp} is a real species", sp in CZ.SPECIES)
for step, sp in AS.PIPELINE_SPECIES.items():
    expect(f"pipeline {step}/{sp} is a real species", sp in CZ.SPECIES)

print("\nidentity carries real parameters")
i = AS.assign("scanner", "observe")
expect("scanner -> NOCTIS", i.species == "NOCTIS", i.species)
expect("tau from the registry", i.tau == CZ.SPECIES["NOCTIS"]["tau"])
expect("innate skill recorded", i.innate_skill == "stealth-harvest", i.innate_skill)
expect("class recorded", i.cls == "Phantom", i.cls)
expect("bounds computed", isinstance(i.bounds, dict) and "may_publish" in i.bounds)

print("\nTHE BOUND MUST ACTUALLY CONSTRAIN — not decorate")
allowed, why = AS.may_publish("shipper")
expect("shipper (SYNTHEX) may publish", allowed is True, why)

noctis = AS._identity("x", "NOCTIS", "observe")
expect("NOCTIS cannot publish", noctis.bounds["may_publish"] is False)
expect("NOCTIS is not cascade-capable", noctis.bounds["cascade_authorised"] is False)
expect("NOCTIS has wide scan width", noctis.bounds["scan_width"] == "wide",
       noctis.bounds["scan_width"])

abyssal = AS._identity("x", "ABYSSAL", "observe")
expect("ABYSSAL cannot publish", abyssal.bounds["may_publish"] is False)

verdant = AS._identity("x", "VERDANT", "orient")
expect("VERDANT cannot publish", verdant.bounds["may_publish"] is False)

for sp in sorted(AS.CASCADE_SPECIES):
    expect(f"{sp} is cascade-capable",
           AS._identity("x", sp, "act").bounds["may_publish"] is True)

print("\nunstable species flagged")
ignis = AS._identity("x", "IGNIS", "decide")
expect("IGNIS (V=14.2) flagged instable", ignis.bounds["instable"] is True,
       str(ignis.bounds))
kronos = AS._identity("x", "KRONOS", "observe")
expect("KRONOS (V=0.8) not flagged instable", kronos.bounds["instable"] is False)

print("\nassign_all persists and is readable")
out = AS.assign_all()
expect("five agents bound", len(out) == 5, str(sorted(out)))
expect("assignment file written", AS.ASSIGNMENT_PATH.exists())
d = json.loads(AS.ASSIGNMENT_PATH.read_text())
expect("file records phase mapping", "phase_mapping" in d)
expect("file records bounds", all("bounds" in v for v in d["agents"].values()))
expect("scanner bound to observe species",
       d["agents"]["scanner"]["species"] in ("NOCTIS", "ABYSSAL"),
       d["agents"]["scanner"]["species"])
expect("shipper bound to act species",
       d["agents"]["shipper"]["species"] in ("SYNTHEX", "LUMARA"),
       d["agents"]["shipper"]["species"])

print("\npipeline steps")
expect("HARVEST->NOCTIS", AS.assign_pipeline_step("HARVEST").species == "NOCTIS")
expect("DEPLOY->SYNTHEX", AS.assign_pipeline_step("DEPLOY").species == "SYNTHEX")
expect("lowercase step works", AS.assign_pipeline_step("scout").species == "AURIX")
for bad, kind in (("NOT_A_STEP", "pipeline"), ("not_a_phase", "phase")):
    try:
        if kind == "pipeline":
            AS.assign_pipeline_step(bad)
        else:
            AS.assign(bad + "_agent", phase=bad)
        expect(f"{kind} '{bad}' raises", False, "no raise")
    except KeyError:
        expect(f"{kind} '{bad}' raises KeyError", True)

print("\nhybrid species params derived, not zeroed")
# ECLIPSE raised KeyError before _species_params() existed.
for hname in ("NEXUS", "ECLIPSE", "WRAITH"):
    p = AS._species_params(hname)
    expect(f"{hname} resolves", isinstance(p, dict))
    expect(f"  {hname} has non-zero tau", p.get("tau", 0) > 0, str(p.get("tau")))
    expect(f"  {hname} has a class", bool(p.get("class")))
expect("NEXUS carries a combined skill",
       "+" in AS._species_params("NEXUS")["skill"],
       AS._species_params("NEXUS")["skill"])
try:
    AS._species_params("NOT_A_SPECIES")
    expect("unknown species still raises", False, "no raise")
except KeyError:
    expect("unknown species still raises KeyError", True)

print("\nstatus")
s = AS.status()
expect("status reports assignments", s["assigned"] == 5, str(s["assigned"]))

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
