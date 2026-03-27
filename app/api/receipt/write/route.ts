export async function POST(req: Request) {
  let body: unknown = null;
  try {
    body = await req.json();
  } catch {}

  return Response.json({
    ok: true,
    route: "/api/receipt/write",
    receipt: body,
    status: "recorded (stub)",
    note: "Persist to DB for durability"
  });
}
