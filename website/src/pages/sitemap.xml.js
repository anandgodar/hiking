export async function GET() {
  const siteUrl = "https://summitseeker.io";
  const lastmod = new Date().toISOString().split('T')[0];

  // Sitemap index — points Googlebot to the two sub-sitemaps.
  // Trail pages: /sitemap-trails.xml  |  Blog + static pages: /sitemap-blog.xml
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>${siteUrl}/sitemap-trails.xml</loc><lastmod>${lastmod}</lastmod></sitemap><sitemap><loc>${siteUrl}/sitemap-blog.xml</loc><lastmod>${lastmod}</lastmod></sitemap></sitemapindex>`;

  return new Response(sitemap, {
    headers: {
      "Content-Type": "application/xml",
      "Cache-Control": "public, max-age=3600"
    }
  });
}
