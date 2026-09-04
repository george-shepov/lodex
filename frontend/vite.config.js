import { readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'
import { SERVICE_ROUTES } from './src/seo.mjs'

const packageMetadata = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'))
const buildVersion = `${packageMetadata.version}+${Date.now().toString(36)}`
const publicRoutePattern = new RegExp(`^https?://[^/]+/(?:$|inspiration/?$|privacy/?$|terms/?$|services/(?:${SERVICE_ROUTES.map(route => route.slug).join('|')})/?$)`)

function buildVersionPlugin() {
  return {
    name: 'lodex-build-version',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'version.json',
        source: JSON.stringify({
          app: 'lodex',
          version: packageMetadata.version,
          build: buildVersion,
        }),
      })
    },
  }
}

export default defineConfig({
  define: {
    __LODEX_APP_VERSION__: JSON.stringify(packageMetadata.version),
    __LODEX_BUILD_VERSION__: JSON.stringify(buildVersion),
  },
  plugins: [
    buildVersionPlugin(),
    vue(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'script',
      includeAssets: [
        'lodex-favicon-32-v2.png',
        'lodex-apple-touch-icon-v2.png',
        'lodex-app-icon-192-v2.png',
        'lodex-app-icon-512-v2.png',
        'lodex-app-icon-maskable-512-v2.png',
      ],
      manifest: {
        name: 'LODEX Home & Business Services',
        short_name: 'LODEX',
        description: 'Start, schedule, and follow LODEX Home, Business, and Enterprise service projects.',
        theme_color: '#0b0d10',
        background_color: '#0b0d10',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        orientation: 'any',
        categories: ['business', 'productivity', 'lifestyle'],
        icons: [
          {
            src: '/lodex-icon-192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: '/lodex-icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: '/lodex-icon-maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        cleanupOutdatedCaches: true,
        clientsClaim: true,
        skipWaiting: true,
        navigateFallback: null,
        globIgnores: ['**/inspiration/**', '**/portfolio/**', '**/services/**', '**/*.mp4'],
        runtimeCaching: [{
          urlPattern: publicRoutePattern,
          handler: 'NetworkFirst',
          method: 'GET',
          options: {
            cacheName: 'lodex-public-pages',
            networkTimeoutSeconds: 4,
            expiration: { maxEntries: 16, maxAgeSeconds: 60 * 60 * 24 * 7 },
          },
        }],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: { proxy: { '/api': 'http://localhost:8015' } },
})
