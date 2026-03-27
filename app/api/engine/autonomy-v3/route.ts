import { evaluateAutonomyV3 } from "@/lib/evez/engine_v3";

export async function GET() {
  const result = evaluateAutonomyV3();
  return Response.json({ ok: true, result });
}
