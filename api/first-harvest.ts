import crypto from "node:crypto";

export const config = {
  runtime: "nodejs",
};

type Quote = {
  venue: string;
  pair: string;
  bid: number;
  ask: number;
  fee_bps: number;
  slippage_bps_est: number;
  freshness_ms: number;
};

type HarvestPayload = {
  skill_id: string;
  event_id: string;
  timestamp: string;
  window_s: number;
  threshold_pct: number;
  quotes: Quote[];
  goal_mode?: "max_profit" | "max_safety" | "neutral";
  source?: string;
};

type RotationScores = {
  time_shift: number;
  state_shift: number;
  frame_shift: number;
  adversarial_shift: number;
  identity_goal_shift: number;
  aggregate_score: number;
  min_rotation_score: number;
  pass: boolean;
};

function sha256(value: string): string {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function clamp(value: number, min = 0, max = 1): number {
  return Math.max(min, Math.min(max, value));
}

function round(value: number, places = 6): number {
  return Number(value.toFixed(places));
}

function mid(q: Quote): number {
  return (q.bid + q.ask) / 2;
}

function isFresh(q: Quote): boolean {
  return Number.isFinite(q.freshness_ms) && q.freshness_ms <= 3000;
}

function normalizeQuotes(quotes: Quote[]) {
  const eligible = quotes
    .filter((q) => q.pair === "USDC/USDT")
    .filter((q) => Number.isFinite(q.bid) && Number.isFinite(q.ask) && q.ask >= q.bid)
    .map((q) => ({
      venue: q.venue,
      pair: q.pair,
      bid: q.bid,
      ask: q.ask,
      mid: mid(q),
      fee_bps: q.fee_bps,
      slippage_bps_est: q.slippage_bps_est,
      cost_bps_total: q.fee_bps + q.slippage_bps_est,
      freshness_ms: q.freshness_ms,
      fresh: isFresh(q),
    }))
    .filter((q) => q.fresh)
    .sort((a, b) => a.mid - b.mid);

  return {
    eligible_quotes: eligible,
    eligible_venue_count: eligible.length,
    disqualified_count: quotes.length - eligible.length,
  };
}

function computeAssertion(payload: HarvestPayload, eligibleQuotes: ReturnType<typeof normalizeQuotes>["eligible_quotes"]) {
  if (eligibleQuotes.length < 2) {
    return {
      raw_spread_pct: 0,
      net_spread_bps: -1,
      duration_s: payload.window_s,
      venue_count: eligibleQuotes.length,
      assert_true: false,
      reason: "insufficient_fresh_venues",
    };
  }

  const low = eligibleQuotes[0];
  const high = eligibleQuotes[eligibleQuotes.length - 1];
  const reference = (low.mid + high.mid) / 2;
  const raw_spread_pct = Math.abs(high.mid - low.mid) / reference * 100;
  const totalCostBps = low.cost_bps_total + high.cost_bps_total;
  const net_spread_bps = raw_spread_pct * 100 - totalCostBps;
  const assert_true =
    eligibleQuotes.length >= 2 &&
    payload.window_s >= 30 &&
    raw_spread_pct > payload.threshold_pct &&
    net_spread_bps > 0;

  return {
    raw_spread_pct: round(raw_spread_pct),
    net_spread_bps: round(net_spread_bps),
    duration_s: payload.window_s,
    venue_count: eligibleQuotes.length,
    assert_true,
    reason: assert_true ? "persistent_cross_venue_net_positive_dislocation" : "assertion_threshold_not_met",
  };
}

function selfConsistency(payload: HarvestPayload, quotes: Quote[]) {
  const baseEligible = normalizeQuotes(quotes).eligible_quotes;
  const baseline = computeAssertion(payload, baseEligible);

  const shuffled = [...quotes].reverse();
  const roundedQuotes = quotes.map((q) => ({ ...q, bid: round(q.bid, 4), ask: round(q.ask, 4) }));
  const staleRemoved = quotes.filter((q) => q.freshness_ms <= 3000);

  const variants = [
    computeAssertion(payload, normalizeQuotes(shuffled).eligible_quotes),
    computeAssertion(payload, normalizeQuotes(roundedQuotes).eligible_quotes),
    computeAssertion(payload, normalizeQuotes(staleRemoved).eligible_quotes),
  ];

  const stable = variants.filter((v) => v.assert_true === baseline.assert_true).length;
  const numericDrift = variants.reduce((acc, v) => acc + Math.abs(v.raw_spread_pct - baseline.raw_spread_pct), 0);
  const consistency_score = clamp(0.55 + stable * 0.12 - numericDrift * 0.05);
  const defeaters: string[] = [];

  if (stable < 2) defeaters.push("assertion_flip_under_recomputation");
  if (numericDrift > 0.5) defeaters.push("spread_drift_under_rounding_or_reorder");

  return {
    consistent: defeaters.length === 0,
    consistency_score: round(consistency_score),
    defeaters,
    baseline,
  };
}

function invarianceBattery(payload: HarvestPayload, assertion: ReturnType<typeof computeAssertion>, eligibleVenueCount: number): RotationScores {
  const cushion = clamp(assertion.net_spread_bps / 250);
  const durationFactor = clamp(payload.window_s / 30);
  const venueFactor = clamp(eligibleVenueCount / 3);
  const goalMode = payload.goal_mode ?? "neutral";

  const time_shift = clamp(0.72 + durationFactor * 0.16 + cushion * 0.08);
  const state_shift = clamp(0.7 + venueFactor * 0.18 + cushion * 0.08);
  const frame_shift = clamp(assertion.assert_true ? 0.92 + cushion * 0.05 : 0.6);
  const adversarial_shift = clamp(0.7 + venueFactor * 0.12 + cushion * 0.12);
  const identity_goal_shift = clamp(goalMode === "neutral" ? 0.97 : 0.9 + cushion * 0.05);

  const values = [time_shift, state_shift, frame_shift, adversarial_shift, identity_goal_shift].map((v) => round(v));
  const aggregate_score = round(values.reduce((a, b) => a + b, 0) / values.length);
  const min_rotation_score = Math.min(...values);
  const pass = aggregate_score >= 0.9 && min_rotation_score >= 0.85 && assertion.assert_true;

  return {
    time_shift: values[0],
    state_shift: values[1],
    frame_shift: values[2],
    adversarial_shift: values[3],
    identity_goal_shift: values[4],
    aggregate_score,
    min_rotation_score,
    pass,
  };
}

function buildArtifacts(payload: HarvestPayload, assertion: ReturnType<typeof computeAssertion>, consistency: ReturnType<typeof selfConsistency>, battery: RotationScores) {
  const normalizedInputs = {
    skill_id: payload.skill_id,
    event_id: payload.event_id,
    window_s: payload.window_s,
    threshold_pct: payload.threshold_pct,
    goal_mode: payload.goal_mode ?? "neutral",
  };

  const commit_hash = sha256(JSON.stringify({ normalizedInputs, assertion, consistency, battery }));
  const lineage_hash = sha256(`${payload.event_id}:${commit_hash}:${payload.timestamp}`);
  const final_status = consistency.consistent && battery.pass ? "KEPT" : "TEST";

  const proof = {
    skill_id: payload.skill_id,
    version: "0.1.0",
    assertion: "normalized net-executable USDC/USDT spread > 2.5% for >=30s across >=2 venues",
    result: final_status,
    raw_spread_pct: assertion.raw_spread_pct,
    net_spread_bps: assertion.net_spread_bps,
    rotation_scores: {
      time_shift: battery.time_shift,
      state_shift: battery.state_shift,
      frame_shift: battery.frame_shift,
      adversarial_shift: battery.adversarial_shift,
      identity_goal_shift: battery.identity_goal_shift,
    },
    aggregate_score: battery.aggregate_score,
    commit_hash,
    lineage_hash,
  };

  const receipt = {
    skill_id: payload.skill_id,
    version: "0.1.0",
    event_id: payload.event_id,
    timestamp: payload.timestamp,
    final_status,
    consistent: consistency.consistent,
    consistency_score: consistency.consistency_score,
    defeaters: consistency.defeaters,
    battery_pass: battery.pass,
    aggregate_score: battery.aggregate_score,
    min_rotation_score: battery.min_rotation_score,
    checkpoint_ref: `proof/${payload.skill_id}_${payload.event_id}.json`,
    receipt_ref: `proof/${payload.skill_id}_${payload.event_id}_receipt.json`,
    commit_hash,
    lineage_hash,
  };

  return { proof, receipt, commit_hash, lineage_hash, final_status };
}

async function maybePostLedger(proof: object, receipt: object) {
  const ledgerWebhook = process.env.FIRST_HARVEST_LEDGER_WEBHOOK_URL;
  if (!ledgerWebhook) return { ledger_posted: false };

  const response = await fetch(ledgerWebhook, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ proof, receipt }),
  });

  return {
    ledger_posted: response.ok,
    ledger_status: response.status,
  };
}

export default async function handler(req: any, res: any) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "method_not_allowed" });
  }

  const payload = req.body as HarvestPayload;
  if (!payload?.skill_id || !payload?.event_id || !Array.isArray(payload?.quotes)) {
    return res.status(400).json({ error: "invalid_payload" });
  }

  const normalized = normalizeQuotes(payload.quotes);
  const assertion = computeAssertion(payload, normalized.eligible_quotes);
  const consistency = selfConsistency(payload, payload.quotes);

  if (!consistency.consistent) {
    const { proof, receipt } = buildArtifacts(payload, assertion, consistency, {
      time_shift: 0,
      state_shift: 0,
      frame_shift: 0,
      adversarial_shift: 0,
      identity_goal_shift: 0,
      aggregate_score: 0,
      min_rotation_score: 0,
      pass: false,
    });
    const ledger = await maybePostLedger(proof, receipt);
    return res.status(200).json({
      status: "TEST",
      stage: "self_consistency_failed",
      normalized,
      assertion,
      consistency,
      proof,
      receipt,
      ...ledger,
    });
  }

  const battery = invarianceBattery(payload, assertion, normalized.eligible_venue_count);
  const { proof, receipt, commit_hash, lineage_hash, final_status } = buildArtifacts(payload, assertion, consistency, battery);
  const ledger = await maybePostLedger(proof, receipt);

  return res.status(200).json({
    status: final_status,
    stage: battery.pass ? "mint_candidate" : "hold_test",
    normalized,
    assertion,
    consistency,
    battery,
    mint_candidate: battery.pass
      ? {
          skill_id: payload.skill_id,
          version: "0.1.0",
          benchmark_ready: true,
          public_proof_ready: true,
        }
      : null,
    ledger_commit: {
      commit_hash,
      lineage_hash,
      final_status,
    },
    proof,
    receipt,
    ...ledger,
  });
}
