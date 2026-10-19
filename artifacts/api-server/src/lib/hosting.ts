/**
 * Production hosting rules for the analysis API.
 *
 * HTTPS is required only when NODE_ENV is production. The Docker healthcheck
 * calls /api/healthz over plain HTTP on localhost, and that path stays open.
 * Rate limiting is a fixed window per client address. It does not store accounts.
 */

const WINDOW_MS = 60_000;

const slots = new Map<string, number[]>();

export function analyzeRateLimitPerMinute(): number {
  const parsed = Number(process.env["ANALYZE_RATE_LIMIT_PER_MINUTE"] ?? 10);
  if (!Number.isFinite(parsed) || parsed < 1) return 10;
  return Math.floor(parsed);
}

export function resetAnalyzeSlots(): void {
  slots.clear();
}

/** True when this client may start another analysis. */
export function takeAnalyzeSlot(key: string, now: number, limit: number, windowMs = WINDOW_MS): boolean {
  const recent = (slots.get(key) ?? []).filter((stamp) => now - stamp < windowMs);
  if (recent.length >= limit) {
    slots.set(key, recent);
    return false;
  }
  recent.push(now);
  slots.set(key, recent);
  return true;
}

export function clientAddress(forwardedFor: string | undefined, remoteAddress: string | undefined): string {
  const forwarded = forwardedFor?.split(",")[0]?.trim();
  return forwarded || remoteAddress || "unknown";
}

export function requestIsHttps(secure: boolean, forwardedProto: string | undefined): boolean {
  if (secure) return true;
  const proto = forwardedProto?.split(",")[0]?.trim().toLowerCase();
  return proto === "https";
}

/** Health checks stay on HTTP so the container probe can reach them. */
export function httpsOnlyApplies(nodeEnv: string | undefined, path: string): boolean {
  if (nodeEnv !== "production") return false;
  return path !== "/api/healthz" && path !== "/healthz";
}
