// @ts-check
import { defineConfig } from 'astro/config';

import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://summitseeker.io',
  integrations: [react()],
  // Tailwind v4 runs as a Vite plugin. It was previously wired through
  // postcss.config.cjs, but Astro 7's Vite pipeline resolves the
  // `@import "tailwindcss"` in global.css with postcss-import before the
  // Tailwind PostCSS plugin sees it, and the build fails looking for a file
  // literally named "tailwindcss".
  vite: {
    plugins: [tailwindcss()]
  },
  compressHTML: true,
  trailingSlash: 'never',
  build: {
    inlineStylesheets: 'auto'
  }
});