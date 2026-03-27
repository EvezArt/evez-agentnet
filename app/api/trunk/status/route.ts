export async function GET() {
  return Response.json({
    ok: true,
    route: "/api/trunk/status",
    system: "EVEZ AgentNet",
    status: "initializing",
    timestamp: new Date().toISOString()
  });
}
