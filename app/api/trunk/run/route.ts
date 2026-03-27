export async function POST(req: Request) {
  let body: unknown = null;
  try {
    body = await req.json();
  } catch {
    body = null;
  }

  return Response.json({
    ok: true,
    route: "/api/trunk/run",
    received: body,
    status: "stub",
    next: "Wire executor or n8n webhook target"
  });
}
