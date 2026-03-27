import { proposeFinanceAction } from "@/lib/evez/finance";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));

  const kind = body?.kind || "payment_link_create";
  const risk = body?.risk || "medium";
  const actor = body?.actor || "operator";
  const summary = body?.summary || "Finance action proposal";
  const payload = body?.payload || {};

  const result = proposeFinanceAction({ kind, risk, actor, summary, payload });
  return Response.json({ ok: true, result });
}
