import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import {
  canonicalForPath,
  PUBLIC_ROUTES,
  SERVICE_ROUTES,
  SITE_URL,
  structuredDataForRoute,
} from '../src/seo.mjs'

assert.equal(PUBLIC_ROUTES.length, 12)
assert.equal(new Set(PUBLIC_ROUTES.map(route => route.path)).size, PUBLIC_ROUTES.length)
assert.equal(new Set(PUBLIC_ROUTES.map(route => route.title)).size, PUBLIC_ROUTES.length)

for (const route of PUBLIC_ROUTES) {
  assert.ok(route.title.length >= 25 && route.title.length <= 70, `${route.path} title length`)
  assert.ok(route.description.length >= 110 && route.description.length <= 170, `${route.path} description length`)
  assert.equal(canonicalForPath(`${route.path}?v=old-build`), `${SITE_URL}${route.path === '/' ? '/' : route.path}`)
  assert.ok(structuredDataForRoute(route)?.['@context'] === 'https://schema.org')
}

assert.equal(canonicalForPath('/not-a-real-route'), null)

const appSource = await readFile(new URL('../src/App.vue', import.meta.url), 'utf8')
const appServiceSlugs = [...appSource.matchAll(/\bslug:\s*'([^']+)'/g)].map(match => match[1])
assert.deepEqual(new Set(appServiceSlugs), new Set(SERVICE_ROUTES.map(route => route.slug)))

const sitemap = await readFile(new URL('../public/sitemap.xml', import.meta.url), 'utf8')
for (const route of PUBLIC_ROUTES) {
  assert.ok(sitemap.includes(`<loc>${SITE_URL}${route.path === '/' ? '/' : route.path}</loc>`), `${route.path} sitemap entry`)
}
assert.ok(!sitemap.includes('/admin'))
assert.ok(!sitemap.includes('/api/'))

const robots = await readFile(new URL('../public/robots.txt', import.meta.url), 'utf8')
assert.match(robots, /^User-agent: \*$/m)
assert.match(robots, /^Sitemap: https:\/\/lodex\.work\/sitemap\.xml$/m)

const nginx = await readFile(new URL('../nginx.conf', import.meta.url), 'utf8')
assert.match(nginx, /location = \/robots\.txt/)
assert.match(nginx, /location = \/sitemap\.xml/)
assert.match(nginx, /try_files \$uri \$uri\.html =404;/)
assert.match(nginx, /absolute_redirect off;/)
assert.doesNotMatch(nginx, /try_files \$uri \/index\.html;/)

console.log('SEO route, sitemap, crawler, and canonical checks passed')
