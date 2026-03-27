export async function POST(req: Request) {
  let body: any = {};
  try {
    body = await req.json();
  } catch {}

  const { lane, message, webhook } = body;

  if (!webhook) {
    return Response.json({ ok: false, error: "Missing webhook URL" }, { status: 400 });
  }

  try {
    await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: message || "[empty]" })
    });

    return Response.json({ ok: true, routed: lane || "unknown" });
  } catch (err) {
    return Response.json({ ok: false, error: "Webhook post failed" }, { status: 500 });
  }
}
