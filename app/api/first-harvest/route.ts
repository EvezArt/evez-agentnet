export async function POST(req: Request) {
  let body: unknown = null;
  try {
    body = await req.json();
  } catch {
    body = null;
  }

  return Response.json({
    ok: true,
    route: "/api/first-harvest",
    received: body,
    status: "stub",
    next: "Implement assertion evaluation logic"
  });
}
