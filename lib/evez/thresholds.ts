export type RankedLane = {
  lane: "digest" | "alerts" | "research" | "integrations";
  score: number;
  reason: string;
  decayedScore?: number;
  cooldownPenalty?: number;
};

export type LaneReceipt = {
  lane?: string;
  timestamp?: string;
};

const DEFAULT_THRESHOLD = 0.45;
const DEFAULT_MAX_ACTIONS = 2;
const HALF_LIFE_MINUTES = 30;
const COOLDOWN_MINUTES = 10;

function minutesSince(timestamp?: string) {
  if (!timestamp) return Number.POSITIVE_INFINITY;
  const then = new Date(timestamp).getTime();
  if (Number.isNaN(then)) return Number.POSITIVE_INFINITY;
  return Math.max(0, (Date.now() - then) / 60000);
}

function decayMultiplier(minutesElapsed: number) {
  if (!Number.isFinite(minutesElapsed)) return 1;
  const exponent = minutesElapsed / HALF_LIFE_MINUTES;
  return 1 - Math.exp(-exponent);
}

function cooldownPenalty(minutesElapsed: number) {
  if (!Number.isFinite(minutesElapsed)) return 0;
  if (minutesElapsed >= COOLDOWN_MINUTES) return 0;
  return Math.max(0, (COOLDOWN_MINUTES - minutesElapsed) / COOLDOWN_MINUTES) * 0.35;
}

export function applyLaneDecay(scores: RankedLane[], receipts: LaneReceipt[]) {
  return scores.map((entry) => {
    const latestForLane = receipts.find((receipt) => receipt?.lane === entry.lane);
    const elapsed = minutesSince(latestForLane?.timestamp);
    const penalty = cooldownPenalty(elapsed);
    const multiplier = decayMultiplier(elapsed);
    const decayedScore = Math.max(0, Math.min(1, entry.score * multiplier - penalty));

    return {
      ...entry,
      decayedScore,
      cooldownPenalty: penalty,
      reason: `${entry.reason} Decay adjusted this lane using ${elapsed.toFixed(2)} minutes since its latest execution and a cooldown penalty of ${penalty.toFixed(2)}.`
    };
  }).sort((a, b) => (b.decayedScore ?? 0) - (a.decayedScore ?? 0));
}

export function chooseActiveLanes(scores: RankedLane[], threshold = DEFAULT_THRESHOLD, maxActions = DEFAULT_MAX_ACTIONS) {
  return scores
    .filter((entry) => (entry.decayedScore ?? entry.score) >= threshold)
    .slice(0, maxActions);
}

export function getThresholdPolicy() {
  return {
    threshold: DEFAULT_THRESHOLD,
    maxActions: DEFAULT_MAX_ACTIONS,
    halfLifeMinutes: HALF_LIFE_MINUTES,
    cooldownMinutes: COOLDOWN_MINUTES,
  };
}
