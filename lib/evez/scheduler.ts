let lastRun = 0;

export function shouldRun(intervalMs: number) {
  const now = Date.now();
  if (now - lastRun > intervalMs) {
    lastRun = now;
    return true;
  }
  return false;
}
