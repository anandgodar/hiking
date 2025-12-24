import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  // REPLACE with your actual domain when you deploy (e.g., https://summitseekerguide.com)
  site: 'https://summitseeker.io',

  integrations: [
    tailwind(),
    react(),
    sitemap()
  ],
});