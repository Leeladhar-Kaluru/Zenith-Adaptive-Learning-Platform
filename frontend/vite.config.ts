import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'zenith-logo.svg', 'zenith-mark.svg'],
      manifest: {
        name: 'ZENITH',
        short_name: 'ZENITH',
        description: 'Curriculum-aware adaptive learning companion for school students',
        theme_color: '#FDFBF7',
        background_color: '#FDFBF7',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          {
            src: '/icon-192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: '/icon-512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: '/maskable-icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable'
          }
        ]
      },
      workbox: {
        // Install only the app shell up front. Lesson chunks, KaTeX and the Hindi/Telugu/handwriting fonts are cached the first
        // time they are used, so a first visit on a slow connection is not competing with a 2 MB background download.
        globPatterns: ['index.html', 'assets/index-*.{js,css}', '*.{ico,png,svg}', 'assets/bricolage-grotesque-latin-wght-normal-*.woff2', 'assets/plus-jakarta-sans-latin-wght-normal-*.woff2'],
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          { urlPattern: ({ url }) => /\/assets\/.+\.(?:js|css)$/.test(url.pathname), handler: 'CacheFirst',
            options: { cacheName: 'zenith-chunks', expiration: { maxEntries: 80, maxAgeSeconds: 60 * 60 * 24 * 60 } } },
          { urlPattern: ({ url }) => /\.(?:woff2?|ttf)$/.test(url.pathname), handler: 'CacheFirst',
            options: { cacheName: 'zenith-fonts', expiration: { maxEntries: 40, maxAgeSeconds: 60 * 60 * 24 * 365 } } }
        ]
      }
    })
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});

