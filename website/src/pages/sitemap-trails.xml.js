export async function GET() {
  const siteUrl = "https://summitseeker.io";

  const allFiles = import.meta.glob('../data/*/*.json', { eager: true });
  const mountainPages = [];
  const states = new Set();
  const discoverTags = new Set();

  const normalizeState = (s) => {
    if (s === 'nh') return 'new-hampshire';
    if (s === 'me') return 'maine';
    if (s === 'vt') return 'vermont';
    if (s === 'ny') return 'new-york';
    if (s === 'ca' || s === 'CA') return 'california';
    return s;
  };

  const escapeXml = (str) => {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  };

  Object.values(allFiles).forEach(file => {
    const m = file.default || file;
    if (!m || m.posts || m.categories) return;
    if (m.title && m.content && !m.elevation) return; // skip blog posts
    if (!m.state_slug || !m.slug) return;

    const stateSlug = normalizeState(m.state_slug);
    states.add(stateSlug);

    mountainPages.push({ url: `${siteUrl}/${stateSlug}/hikes/${m.slug}`, mountain: m });

    const tags = [
      ...(m.tags || []),
      ...(m.features?.map(f => f.type) || []),
      m.trails?.[0]?.stats?.difficulty
    ].filter(Boolean);

    tags.forEach(t => {
      const cleanTag = t.toString().toLowerCase().trim()
        .replace(/_/g, '-').replace(/\s+/g, '-').replace(/s$/, '').replace(/[^\w\-]+/g, '');
      if (cleanTag) discoverTags.add(cleanTag);
    });
  });

  const lastmod = new Date().toISOString().split('T')[0];

  const urls = [
    // Homepage
    `<url><loc>${siteUrl}/</loc><lastmod>${lastmod}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>`,
    // Challenge pages
    `<url><loc>${siteUrl}/challenges/nh-48-4000-footers</loc><lastmod>${lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>`,
    // State pages
    ...[...states].map(s =>
      `<url><loc>${siteUrl}/${s}</loc><lastmod>${lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>`
    ),
    // Near me pages
    ...['boston','portland-maine','burlington-vermont','los-angeles','new-york-city','san-francisco'].map(city =>
      `<url><loc>${siteUrl}/near/${city}</loc><lastmod>${lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.85</priority></url>`
    ),
    // Discover tag pages
    ...[...discoverTags].map(t =>
      `<url><loc>${siteUrl}/discover/${t}</loc><lastmod>${lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>`
    ),
    // Mountain trail pages (with image sitemaps)
    ...mountainPages.map(({ url, mountain: m }) => {
      const imageTag = m.mountain_hero
        ? `<image:image><image:loc>${escapeXml(m.mountain_hero)}</image:loc><image:title>${escapeXml(m.name)} Hiking Trail</image:title><image:caption>Hiking trail to ${escapeXml(m.name)}${m.elevation ? ` summit at ${m.elevation} feet` : ''}</image:caption></image:image>`
        : '';
      return `<url><loc>${escapeXml(url)}</loc><lastmod>${lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority>${imageTag}</url>`;
    })
  ];

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">${urls.join('')}</urlset>`;

  return new Response(sitemap, {
    headers: {
      "Content-Type": "application/xml",
      "Cache-Control": "public, max-age=3600"
    }
  });
}
