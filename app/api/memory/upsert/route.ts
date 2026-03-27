export async function POST(req: Request) {
  let body: unknown = null;
  try {
    body = await req.json();
  } catch {}

  return Response.json({
    ok: true,
    route: "/api/memory/upsert",
    stored: body,
    status: "stub",
    note: "Replace with DB or KV store"
  });
}
