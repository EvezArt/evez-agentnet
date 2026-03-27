import { evaluateAutonomyV4, executeLanePayloads } from "@/lib/evez/engine_v4";

export async function POST() {
  const decision = evaluateAutonomyV4();

  if (decision.payloads.length === 0) {
    return Response.json({ ok: true, mode: "idle", decision });
  }

  const execution = executeLanePayloads(decision);

  return Response.json({
    ok: true,
    mode: "tailored-multi-action",
    decision,
    execution,
  });
}
