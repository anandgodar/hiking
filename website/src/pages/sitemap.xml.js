import { execSync } from 'node:child_process';
import { isPublishReady } from '../lib/publishReady.js';

// Real per-trail lastmod, derived from each data file's most recent git
// commit — git history survives a fresh checkout, filesystem mtimes don't,
// which is why every URL previously shared one build-time date. Scoped to
// mountain pages for now (they're 1:1 with a single source file); aggregate
// pages (state hubs, near-me, discover tags) aren't tied to one file and are
// left on the build date as a follow-up.
function buildGitLastmodMap() {
  const map = new Map();
  try {
    const log = execSync('git log --format="C:%cI" --name-only', {
      encoding: 'utf8',
      maxBuffer: 1024 * 1024 * 64
    });
    let currentDate = null;
    for (const line of log.split('\n')) {
      if (line.startsWith('C:')) {
        currentDate = line.slice(2).trim();
      } else if (line.trim() && currentDate) {
        const path = line.trim();
        if (!map.has(path)) map.set(path, currentDate.slice(0, 10));
      }
    }
  } catch {
    // Not in a git checkout (or git unavailable) — callers fall back to the
    // build-time blanket date.
  }
  return map;
}

// A mountain page's rendered HTML also changes when the shared page
// template itself changes (as this very commit does, adding Albany links to
// [state]/hikes/[slug].astro) even though no data file was touched — so its
// lastmod needs to be at least as recent as the template's own last commit.
const maxDate = (...dates) => dates.filter(Boolean).sort().pop() || null;

export async function GET() {
  const siteUrl = "https://summitseeker.io";
  const gitLastmod = buildGitLastmodMap();
  const pageTemplateLastmod = gitLastmod.get('website/src/pages/[state]/hikes/[slug].astro');

  // 1. Gather Data
  const allFiles = await import.meta.glob('../data/*/*.json', { eager: true });
  const pages = [];

  // 2. Add Homepage with highest priority
  pages.push({ url: `${siteUrl}/`, priority: 1.0, changefreq: 'daily' });

  // 2.1 Add Blog, Guides, and Gear hub pages (high priority for monetization)
  pages.push({ url: `${siteUrl}/blog`, priority: 0.9, changefreq: 'daily' });
  pages.push({ url: `${siteUrl}/map`, priority: 0.9, changefreq: 'weekly' });
  pages.push({ url: `${siteUrl}/guides`, priority: 0.85, changefreq: 'weekly' });
  pages.push({ url: `${siteUrl}/gear`, priority: 0.85, changefreq: 'weekly' });

  // 2.2 Add individual guide pages
  const guideSlugs = [
    'white-mountains-complete-guide',
    'acadia-national-park-guide',
    'vermont-long-trail-guide',
    'california-day-hikes-guide',
    'nh-4000-footers-guide',
    'adirondack-46ers-guide',
    'winter-hiking-new-england',
    'fall-foliage-hiking-guide'
  ];
  guideSlugs.forEach(slug => {
    pages.push({ url: `${siteUrl}/guides/${slug}`, priority: 0.8, changefreq: 'weekly' });
  });

  // 2.3 Add challenge pages (high priority - peak bagging lists)
  const challengePages = [
    { slug: 'nh-48-4000-footers', title: 'NH 48 4000-Footers' },
    // Future challenge pages:
    // { slug: 'adirondack-46ers', title: 'Adirondack 46ers' },
    // { slug: 'new-england-67', title: 'New England 67' },
  ];
  challengePages.forEach(challenge => {
    pages.push({ url: `${siteUrl}/challenges/${challenge.slug}`, priority: 0.9, changefreq: 'weekly' });
  });

  const states = new Set();
  const discoverTags = new Set();
  const mountainPages = [];
  const blogPages = [];

  // Normalize State Slug helper
  const normalizeState = (s) => {
    if (s === 'nh') return 'new-hampshire';
    if (s === 'me') return 'maine';
    if (s === 'vt') return 'vermont';
    if (s === 'ny') return 'new-york';
    if (s === 'ca' || s === 'CA') return 'california';
    return s;
  };

  Object.entries(allFiles).forEach(([globKey, file]) => {
    const m = file.default;
    // globKey is relative to this file (website/src/pages/), e.g.
    // '../data/new-hampshire/mount-washington-nh.json' — resolve to the
    // repo-root-relative path git log reports.
    const repoPath = 'website/src/data/' + globKey.replace(/^\.\.\/data\//, '');

    // Skip blog index file
    if (m.posts || m.categories) return;

    // Handle blog posts (have title and content but no elevation)
    if (m.title && m.content && !m.elevation && m.slug) {
      blogPages.push({
        url: `${siteUrl}/blog/${m.slug}`,
        priority: 0.8,
        changefreq: 'weekly',
        post: m
      });
      return;
    }

    // Skip if no state_slug (not a mountain)
    if (!m.state_slug) return;

    // Skip draft/route-incomplete trails — never submit thin pages to search.
    if (!isPublishReady(m)) return;

    const stateSlug = normalizeState(m.state_slug);
    states.add(stateSlug);

    // Add Mountain Page with high priority (main content)
    mountainPages.push({
      url: `${siteUrl}/${stateSlug}/hikes/${m.slug}`,
      priority: 0.9,
      changefreq: 'weekly',
      mountain: m,
      lastmod: maxDate(gitLastmod.get(repoPath), pageTemplateLastmod) // null falls back to the blanket build date below
    });

    // Collect Tags for Discover Pages
    const tags = [
        ...(m.tags || []),
        ...(m.features?.map(f => f.type) || []),
        m.trails?.[0]?.stats?.difficulty
    ].filter(Boolean);

    tags.forEach(t => {
        // Singularize and normalize
        const cleanTag = t.toString().toLowerCase().trim()
            .replace(/_/g, '-')
            .replace(/\s+/g, '-')
            .replace(/s$/, '')
            .replace(/[^\w\-]+/g, '');
        if (cleanTag) discoverTags.add(cleanTag);
    });
  });

  // 3. Add State Pages (medium-high priority)
  states.forEach(s => {
      pages.push({
        url: `${siteUrl}/${s}`,
        priority: 0.8,
        changefreq: 'weekly'
      });
      // Programmatic "highest peaks in <state>" listicle
      pages.push({
        url: `${siteUrl}/${s}/highest-peaks`,
        priority: 0.75,
        changefreq: 'weekly'
      });
  });

  // 4. Add "Near Me" pages (high priority - local SEO)
  const nearMePages = [
    { city: 'boston', priority: 0.85 },
    { city: 'portland-maine', priority: 0.85 },
    { city: 'burlington-vermont', priority: 0.85 },
    { city: 'los-angeles', priority: 0.85 },
    { city: 'new-york-city', priority: 0.85 },
    { city: 'san-francisco', priority: 0.85 },
    { city: 'providence', priority: 0.85 },
    { city: 'hartford', priority: 0.85 },
    { city: 'albany', priority: 0.85 },
    { city: 'philadelphia', priority: 0.85 },
    { city: 'pittsburgh', priority: 0.85 }
  ];

  // Programmatic city pages (near/[city].astro) — mirror its ≥5-trails-
  // within-100mi rule so we never sitemap a page that wasn't generated.
  try {
    const cities = (await import('../data-static/cities.json')).default;
    const hav = (aLat, aLon, bLat, bLon) => {
      const R = 3959;
      const dLat = (bLat - aLat) * Math.PI / 180;
      const dLon = (bLon - aLon) * Math.PI / 180;
      const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(aLat * Math.PI / 180) * Math.cos(bLat * Math.PI / 180) *
        Math.sin(dLon / 2) ** 2;
      return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    };
    const liveCoords = [];
    Object.values(allFiles).forEach(mod => {
      const m = mod.default || mod;
      if (m && m.lat && m.lon && isPublishReady(m)) liveCoords.push([m.lat, m.lon]);
    });
    cities.forEach(c => {
      const n = liveCoords.filter(([la, lo]) => hav(c.lat, c.lon, la, lo) <= 100).length;
      if (n >= 5) nearMePages.push({ city: c.slug, priority: 0.85 });
    });
  } catch { /* cities file optional */ }

  nearMePages.forEach(({ city, priority }) => {
    pages.push({
      url: `${siteUrl}/near/${city}`,
      priority: priority,
      changefreq: 'weekly'
    });
  });

  // 5. Add Discover tag pages (medium priority)
  discoverTags.forEach(t => {
      pages.push({
        url: `${siteUrl}/discover/${t}`,
        priority: 0.7,
        changefreq: 'weekly'
      });
  });

  // 6. Add static pages (lower priority)
  pages.push({ url: `${siteUrl}/about`, priority: 0.5, changefreq: 'monthly' });
  pages.push({ url: `${siteUrl}/contact`, priority: 0.5, changefreq: 'monthly' });
  pages.push({ url: `${siteUrl}/privacy`, priority: 0.3, changefreq: 'monthly' });
  pages.push({ url: `${siteUrl}/terms`, priority: 0.3, changefreq: 'monthly' });
  pages.push({ url: `${siteUrl}/disclaimer`, priority: 0.3, changefreq: 'monthly' });

  // 7. XML escape function to prevent parsing errors
  const escapeXml = (str) => {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  };

  // 8. Generate XML with images
  const lastmod = new Date().toISOString().split('T')[0];
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
      ${pages.map(page => `
        <url>
          <loc>${escapeXml(page.url)}</loc>
          <lastmod>${lastmod}</lastmod>
          <changefreq>${page.changefreq}</changefreq>
          <priority>${page.priority}</priority>
        </url>
      `).join('')}
      ${mountainPages.map(page => {
        const m = page.mountain;
        return `
        <url>
          <loc>${escapeXml(page.url)}</loc>
          <lastmod>${page.lastmod || lastmod}</lastmod>
          <changefreq>${page.changefreq}</changefreq>
          <priority>${page.priority}</priority>${m?.mountain_hero ? `
          <image:image>
            <image:loc>${escapeXml(m.mountain_hero)}</image:loc>
            <image:title>${escapeXml(m.name)} Trail</image:title>
            <image:caption>Hiking trail to ${escapeXml(m.name)}${m.elevation ? ` summit at ${m.elevation} feet` : ''}</image:caption>
          </image:image>` : ''}
        </url>
        `;
      }).join('')}
      ${blogPages.map(page => {
        const p = page.post;
        return `
        <url>
          <loc>${escapeXml(page.url)}</loc>
          <lastmod>${p.updated || p.date || lastmod}</lastmod>
          <changefreq>${page.changefreq}</changefreq>
          <priority>${page.priority}</priority>${p?.featured_image ? `
          <image:image>
            <image:loc>${escapeXml(p.featured_image)}</image:loc>
            <image:title>${escapeXml(p.title)}</image:title>
            <image:caption>${escapeXml(p.excerpt || p.title)}</image:caption>
          </image:image>` : ''}
        </url>
        `;
      }).join('')}
    </urlset>`;

  return new Response(sitemap, {
    headers: {
      "Content-Type": "application/xml",
      "Cache-Control": "public, max-age=3600"
    }
  });
}