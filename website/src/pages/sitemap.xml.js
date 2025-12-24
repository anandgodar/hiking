export async function GET() {
  const siteUrl = "https://summitseeker.io"; // REPLACE THIS with your actual domain when deployed

  // 1. Gather Data
  const allFiles = await import.meta.glob('../data/*/*.json', { eager: true });
  const pages = new Set();

  // 2. Add Static & Category Pages
  pages.add(`${siteUrl}/`);
  pages.add(`${siteUrl}/privacy`);
  pages.add(`${siteUrl}/terms`);

  const states = new Set();
  const discoverTags = new Set();

  Object.values(allFiles).forEach(file => {
    const m = file.default;

    // Normalize State Slug
    const stateSlug = m.state_slug === 'nh' ? 'new-hampshire' : m.state_slug;
    states.add(stateSlug);

    // Add Mountain Page
    pages.add(`${siteUrl}/${stateSlug}/${m.slug}`);

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

  // 3. Add State & Discover URLs
  states.forEach(s => {
      pages.add(`${siteUrl}/${s}`);
      discoverTags.forEach(t => {
          pages.add(`${siteUrl}/${s}/hikes/${t}`);
      });
  });

  discoverTags.forEach(t => {
      pages.add(`${siteUrl}/discover/${t}`);
  });

  // 4. Generate XML
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      ${[...pages].map(url => `
        <url>
          <loc>${url}</loc>
          <lastmod>${new Date().toISOString().split('T')[0]}</lastmod>
          <changefreq>weekly</changefreq>
          <priority>0.8</priority>
        </url>
      `).join('')}
    </urlset>`;

  return new Response(sitemap, {
    headers: {
      "Content-Type": "application/xml",
      "Cache-Control": "public, max-age=3600"
    }
  });
}