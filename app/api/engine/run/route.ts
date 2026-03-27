import { parseCommandText, runIntent } from "@/lib/evez/engine";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const text = typeof body?.text === "string" ? body.text : "";

  const intent = parseCommandText(text);
  if (!intent) {
    return Response.json({ ok: false, error: "Invalid command" }, { status: 400 });
  }

  const result = runIntent(intent);

  return Response.json({ ok: true, result });
}
