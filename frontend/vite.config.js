import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { services, servicePath } from './src/services.js'

function servicePages() {
  return {
    name: 'lodex-service-pages',
    generateBundle(_, bundle) {
      const jsFile = Object.keys(bundle).find(file => file.endsWith('.js'))
      const cssFile = Object.keys(bundle).find(file => file.endsWith('.css'))
      if (!jsFile) return
      services.forEach(service => {
        const title = `${service.name} in Northeast Ohio | LODEX Home Services`
        const html = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><meta name="description" content="${service.seo}"><link rel="canonical" href="https://lodex.giorgiy.org${servicePath(service)}"><meta name="theme-color" content="#0b2623"><title>${title}</title>${cssFile ? `<link rel="stylesheet" href="/${cssFile}">` : ''}</head><body><div id="app"></div><script type="module" src="/${jsFile}"></script></body></html>`
        this.emitFile({ type: 'asset', fileName: `services/${service.slug}/index.html`, source: html })
      })
    },
  }
}

export default defineConfig({
  plugins: [vue(), servicePages()],
  server: { proxy: { '/api': 'http://localhost:8015' } },
})
