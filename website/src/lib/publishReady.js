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
export function isPublishReady(mountain) {
  if (!mountain || !mountain.name || !mountain.slug) return false;
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
