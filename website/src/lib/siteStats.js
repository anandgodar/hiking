/**
 * Single source of truth for site-wide trail and state counts.
 *
 * These numbers appeared three times on the homepage with three different
 * values ("905+ trails across 48 states", "900+ across all 50 states",
 * "800+ summits") because two of them were hardcoded strings that went stale.
 * Anything that states a count must import it from here.
 */
import { isPublishReady } from './publishReady.js';

const normalizeState = (s) => {
  if (s === 'nh') return 'new-hampshire';
  if (s === 'me') return 'maine';
  if (s === 'vt') return 'vermont';
  if (s === 'ny') return 'new-york';
  return s;
};

const files = import.meta.glob('../data/*/*.json', { eager: true });

const liveTrails = Object.values(files)
  .map((f) => f.default || f)
  .filter((m) => m && m.state_slug)
  .filter(isPublishReady);

/** Number of published trail guides. */
export const trailCount = liveTrails.length;

/** Number of states with at least one published trail. */
export const stateCount = new Set(
  liveTrails.map((m) => normalizeState(m.state_slug))
).size;

/** "900+" style figure, rounded DOWN so the claim is never an overstatement. */
export const trailCountRounded = Math.floor(trailCount / 100) * 100;
