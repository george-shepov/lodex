import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      registerType: 'prompt',
      injectRegister: 'script',
      includeAssets: ['lodex-icon.svg'],
      manifest: {
        name: 'LODEX Residential & Commercial Services',
        short_name: 'LODEX',
        description: 'Start, schedule, and follow residential or commercial LODEX service projects.',
        theme_color: '#17212b',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        orientation: 'any',
        categories: ['business', 'productivity', 'lifestyle'],
        icons: [
          {
            src: '/lodex-icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api\//],
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
