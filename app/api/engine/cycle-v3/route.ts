import { evaluateAutonomyV3, executeLaneSet } from "@/lib/evez/engine_v3";

export async function POST() {
  const decision = evaluateAutonomyV3();

  if (decision.activeLanes.length === 0) {
    return Response.json({ ok: true, mode: "idle", decision });
  }

  const execution = executeLaneSet(decision);

  return Response.json({
    ok: true,
    mode: "multi-action",
    decision,
    execution,
  });
}
