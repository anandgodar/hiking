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
    const stateSlug = m.state_slug === 'nh' ? 'new-hampshire' : m.state_slug;
    states.add(stateSlug);

    // Add Mountain Page with high priority (main content)
    mountainPages.push({
      url: `${siteUrl}/${stateSlug}/hikes/${m.slug}`,
      priority: 0.9,
      changefreq: 'weekly'
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

  // 4. Add State-specific tag pages (medium priority)
  states.forEach(s => {
      discoverTags.forEach(t => {
          pages.push({
            url: `${siteUrl}/${s}/hikes/${t}`,
            priority: 0.6,
            changefreq: 'weekly'
          });
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
  pages.push({ url: `${siteUrl}/privacy`, priority: 0.3, changefreq: 'monthly' });
  pages.push({ url: `${siteUrl}/terms`, priority: 0.3, changefreq: 'monthly' });

  // 7. Combine all pages
  const allPages = [...pages, ...mountainPages];

  // 8. Generate XML with images
  const lastmod = new Date().toISOString().split('T')[0];
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
            xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
      ${allPages.map(page => `
        <url>
          <loc>${page.url}</loc>
          <lastmod>${lastmod}</lastmod>
          <changefreq>${page.changefreq}</changefreq>
          <priority>${page.priority}</priority>
        </url>
      `).join('')}
      ${mountainPages.map(page => {
        const mountain = Object.values(allFiles).find(f => {
          const m = f.default || f;
          return page.url.includes(m.slug);
        });
        const m = mountain?.default || mountain;
        return m?.mountain_hero ? `
        <url>
          <loc>${page.url}</loc>
          <lastmod>${lastmod}</lastmod>
          <changefreq>${page.changefreq}</changefreq>
          <priority>${page.priority}</priority>
          <image:image>
            <image:loc>${m.mountain_hero}</image:loc>
            <image:title>${m.name} Trail</image:title>
            <image:caption>Hiking trail to ${m.name} summit at ${m.elevation} feet</image:caption>
          </image:image>
        </url>
        ` : '';
      }).join('')}
    </urlset>`;

  return new Response(sitemap, {
    headers: {
      "Content-Type": "application/xml",
      "Cache-Control": "public, max-age=3600"
    }
  });
}