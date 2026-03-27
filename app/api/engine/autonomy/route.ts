import { evaluateAutonomy } from "@/lib/evez/engine";

export async function GET() {
  const result = evaluateAutonomy();

  return Response.json({ ok: true, result });
}
