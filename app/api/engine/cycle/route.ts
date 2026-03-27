import { evaluateAutonomy, runIntent } from "@/lib/evez/engine";

export async function POST() {
  const autonomy = evaluateAutonomy();

  if (!autonomy.shouldDigest) {
    return Response.json({ ok: true, mode: "idle", autonomy });
  }

  const result = runIntent({
    kind: "digest",
    lane: "digest",
    payload: {
      source: "autonomy",
      digest: autonomy.digest,
    },
  });

  return Response.json({ ok: true, mode: "reactive", autonomy, result });
}
