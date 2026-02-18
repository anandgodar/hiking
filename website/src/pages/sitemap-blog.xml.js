export async function GET() {
  const siteUrl = "https://summitseeker.io";

  const allFiles = import.meta.glob('../data/blog/*.json', { eager: true });
  const blogPages = [];

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
    if (!m || m.posts || m.categories) return; // skip index.json
    if (m.slug && m.title && m.content) {
      blogPages.push({ url: `${siteUrl}/blog/${m.slug}`, post: m });
    }
  });

  const lastmod = new Date().toISOString().split('T')[0];

  // Guide slugs
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

  const urls = [
    // Blog & guides hubs
    `<url><loc>${siteUrl}/blog</loc><lastmod>${lastmod}</lastmod><changefreq>daily</changefreq><priority>0.9</priority></url>`,
    `<url><loc>${siteUrl}/guides</loc><lastmod>${lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.85</priority></url>`,
    `<url><loc>${siteUrl}/gear</loc><lastmod>${lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.85</priority></url>`,
    // Guide pages
    ...guideSlugs.map(slug =>
      `<url><loc>${siteUrl}/guides/${slug}</loc><lastmod>${lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>`
    ),
    // Static pages
    `<url><loc>${siteUrl}/about</loc><lastmod>${lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>`,
    `<url><loc>${siteUrl}/contact</loc><lastmod>${lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>`,
    `<url><loc>${siteUrl}/privacy</loc><lastmod>${lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.3</priority></url>`,
    `<url><loc>${siteUrl}/terms</loc><lastmod>${lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.3</priority></url>`,
    `<url><loc>${siteUrl}/disclaimer</loc><lastmod>${lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.3</priority></url>`,
    // Blog posts
    ...blogPages.map(({ url, post: p }) => {
      const imageTag = p.featured_image
        ? `<image:image><image:loc>${escapeXml(p.featured_image)}</image:loc><image:title>${escapeXml(p.title)}</image:title><image:caption>${escapeXml(p.excerpt || p.title)}</image:caption></image:image>`
        : '';
      return `<url><loc>${escapeXml(url)}</loc><lastmod>${p.updated || p.date || lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority>${imageTag}</url>`;
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
