export async function GET() {
  const siteUrl = "https://summitseeker.io";

  // 1. Gather Data
  const allFiles = await import.meta.glob('../data/*/*.json', { eager: true });
  const pages = [];

  // 2. Add Homepage with highest priority
  pages.push({ url: `${siteUrl}/`, priority: 1.0, changefreq: 'daily' });

  const states = new Set();
  const discoverTags = new Set();
  const mountainPages = [];

  Object.values(allFiles).forEach(file => {
    const m = file.default;

    // Normalize State Slug
    const normalizeState = (s) => {
      if (s === 'nh') return 'new-hampshire';
      if (s === 'me') return 'maine';
      if (s === 'vt') return 'vermont';
      if (s === 'ny') return 'new-york';
      if (s === 'ca' || s === 'CA') return 'california';
      return s;
    };

    const stateSlug = normalizeState(m.state_slug);
    states.add(stateSlug);

    // Add Mountain Page with high priority (main content)
    mountainPages.push({
      url: `${siteUrl}/${stateSlug}/hikes/${m.slug}`,
      priority: 0.9,
      changefreq: 'weekly',
      mountain: m
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
  });

  // 4. Add "Near Me" pages (high priority - local SEO)
  const nearMePages = [
    { city: 'boston', priority: 0.85 },
    { city: 'portland-maine', priority: 0.85 },
    { city: 'burlington-vermont', priority: 0.85 },
    { city: 'los-angeles', priority: 0.85 }
  ];

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
          <lastmod>${lastmod}</lastmod>
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
    </urlset>`;

  return new Response(sitemap, {
    headers: {
      "Content-Type": "application/xml",
      "Cache-Control": "public, max-age=3600"
    }
  });
}