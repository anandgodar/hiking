/**
 * Publish-readiness gate for trails.
 *
 * A trail is only shown on the public site once it has a verified route — a
 * real GPS path and a distance — and is no longer marked as a draft import
 * (`_status`). This keeps thin, routeless stub pages (e.g. fresh OpenStreetMap
 * imports) out of the build, protecting trust and SEO. Finish a draft by
 * filling its route data and removing the `_status` key; it then goes live
 * automatically.
 */
/**
 * Local preview escape hatch: set SHOW_DRAFTS=1 to reveal draft trails while
 * developing (e.g. `SHOW_DRAFTS=1 npm run dev`). A normal production build does
 * NOT set it, so drafts stay hidden where it matters. Only the basic
 * "is this a real trail file" checks still apply.
 */
const SHOW_DRAFTS = (() => {
  try {
    return !!(import.meta.env && (import.meta.env.SHOW_DRAFTS || import.meta.env.PUBLIC_SHOW_DRAFTS));
  } catch {
    return false;
  }
})();

export function isPublishReady(mountain) {
  if (!mountain || !mountain.name || !mountain.slug) return false;
  if (SHOW_DRAFTS) return true; // local preview: show everything
  if (mountain._status) return false; // draft / imported-unverified
  const trail = (mountain.trails && mountain.trails[0]) || {};
  const hasPath = Array.isArray(trail?.geo?.path) && trail.geo.path.length > 0;
  const dist = trail?.stats?.distance;
  const hasDistance = typeof dist === 'number' && dist > 0;
  return hasPath && hasDistance;
}

/** Filter a list of mountains to only those ready to publish. */
export function publishReady(mountains) {
  return (mountains || []).filter(isPublishReady);
}
