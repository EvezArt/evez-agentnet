import { evaluateAutonomyV4 } from "@/lib/evez/engine_v4";

export async function GET() {
  const result = evaluateAutonomyV4();
  return Response.json({ ok: true, result });
}
