import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { dirname, join } from 'node:path'
import {
  PUBLIC_ROUTES,
  SERVICE_ROUTES,
  SITE_NAME,
  SITE_URL,
  SOCIAL_IMAGE,
  structuredDataForRoute,
} from '../src/seo.mjs'

const distDir = new URL('../dist/', import.meta.url)
const template = await readFile(new URL('index.html', distDir), 'utf8')

function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function safeJson(value) {
  return JSON.stringify(value).replaceAll('<', '\\u003c')
}

function headFor(route, { noindex = false } = {}) {
  const canonical = route?.path ? `${SITE_URL}${route.path === '/' ? '/' : route.path}` : ''
  const title = route?.title || `Private workspace | ${SITE_NAME}`
  const description = route?.description || 'Private LODEX application workspace.'
  const schema = route?.path ? structuredDataForRoute(route) : null
  return [
    `<meta name="description" content="${escapeHtml(description)}" />`,
    `<meta name="robots" content="${noindex ? 'noindex,nofollow' : 'index,follow'}" />`,
    canonical ? `<link rel="canonical" href="${canonical}" />` : '',
    '<meta property="og:type" content="website" />',
    `<meta property="og:site_name" content="${SITE_NAME}" />`,
    `<meta property="og:title" content="${escapeHtml(title)}" />`,
    `<meta property="og:description" content="${escapeHtml(description)}" />`,
    canonical ? `<meta property="og:url" content="${canonical}" />` : '',
    `<meta property="og:image" content="${SOCIAL_IMAGE}" />`,
    `<meta property="og:image:alt" content="${SITE_NAME}" />`,
    '<meta name="twitter:card" content="summary_large_image" />',
    `<meta name="twitter:title" content="${escapeHtml(title)}" />`,
    `<meta name="twitter:description" content="${escapeHtml(description)}" />`,
    `<meta name="twitter:image" content="${SOCIAL_IMAGE}" />`,
    schema ? `<script id="lodex-structured-data" type="application/ld+json">${safeJson(schema)}</script>` : '',
  ].filter(Boolean).join('\n    ')
}

function sharedNav() {
  return `<div class="utility-bar"><span>Northeast Ohio · Residential &amp; commercial</span><a href="tel:+14406018001">Call LODEX · (440) 601-8001</a></div>
  <nav class="site-nav" aria-label="Primary navigation"><a class="brand" href="/"><img class="brand-logo" src="/lodex-logo-home-business.webp" alt="LODEX Home &amp; Business Services" width="340" height="102" /></a><div class="nav-links"><a href="/#services">Services</a><a href="/inspiration">Inspiration</a><a href="/#how-it-works">How it works</a></div><a class="nav-cta" href="/#intake">Start a project <span>↗</span></a></nav>`
}

function sharedFooter() {
  return `<footer class="site-footer"><div class="footer-shell"><section class="footer-intro"><a class="footer-brand-link" href="/"><img class="footer-logo" src="/lodex-logo-home-business.webp" alt="LODEX Home &amp; Business Services" width="340" height="102" /></a><p>Residential and commercial property improvement services across Northeast Ohio.</p></section><nav class="footer-group"><span>Services</span>${SERVICE_ROUTES.map(route => `<a href="${route.path}">${escapeHtml(route.h1)}</a>`).join('')}</nav><nav class="footer-group"><span>Explore</span><a href="/inspiration">Inspiration archive</a><a href="/privacy">Privacy Policy</a><a href="/terms">Terms &amp; Conditions</a></nav></div></footer>`
}

function renderHome(route) {
  return `<section class="hero page-width"><div class="hero-copy"><p class="eyebrow">LODEX · Northeast Ohio</p><h1>${escapeHtml(route.h1)}</h1><p class="lede">${escapeHtml(route.intro)}</p><div class="hero-actions"><a class="primary-button" href="/#intake">Start with your project <span>↗</span></a><a class="phone-link" href="tel:+14406018001">Call (440) 601-8001</a></div></div><div class="hero-visual"><img class="hero-reel-media brand-logo-slide" src="/lodex-logo-home-business.webp" alt="LODEX Home &amp; Business Services" width="1254" height="1254" /></div></section>
  <section id="services" class="services-section page-width"><div class="section-heading"><div><p class="eyebrow">LODEX services</p><h2>Renovate, repair, deliver, source, and restore.</h2></div><p>Choose a service to review practical scope, common use cases, and the next step.</p></div><div class="service-grid">${SERVICE_ROUTES.map((service, index) => `<a class="service-card" href="${service.path}"><span>0${index + 1}</span><h3>${escapeHtml(service.h1)}</h3><p>${escapeHtml(service.description)}</p><b>Explore service →</b></a>`).join('')}</div></section>`
}

function renderService(route) {
  return `<section class="service-hero page-width"><nav class="seo-breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a><span>›</span><a href="/#services">Services</a><span>›</span><span aria-current="page">${escapeHtml(route.h1)}</span></nav><div class="service-hero-grid"><div><p class="eyebrow">LODEX services</p><h1>${escapeHtml(route.h1)}</h1><p class="service-lede">${escapeHtml(route.intro)}</p><div class="hero-actions"><a class="primary-button" href="/#intake">Start this project <span>↗</span></a><a class="phone-link" href="tel:+14406018001">Call (440) 601-8001</a></div></div><div class="service-hero-media"><img class="service-reel-image" src="${route.image}" alt="${escapeHtml(route.h1)}" width="1254" height="1254" /></div></div></section><section class="service-details page-width"><div><p class="section-kicker">Included services</p><ul>${route.includes.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div><div><p class="section-kicker">A good fit when</p><ul>${route.useCases.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div></section><section class="service-next"><div class="page-width"><p class="eyebrow">Start with the real details</p><h2>Photo, video, or a few plain words is enough to begin.</h2><a class="primary-button" href="/#intake">Tell us about it <span>↗</span></a></div></section>`
}

function renderOther(route) {
  if (route.kind === 'collection') {
    return `<section class="gallery-hero page-width"><a class="back-link" href="/">← LODEX home</a><p class="eyebrow">LODEX inspiration archive</p><div class="gallery-hero-grid"><div><h1>${escapeHtml(route.h1)}</h1></div><div><p>${escapeHtml(route.intro)}</p></div></div></section><section class="gallery-cta"><div class="page-width"><p class="eyebrow">Turn inspiration into a real scope</p><h2>Show us the idea and the space you actually have.</h2><a class="primary-button" href="/#intake">Start your project <span>↗</span></a> <a class="phone-link" href="/services/contracting-renovations">Explore renovation services</a></div></section>`
  }
  return `<article class="legal-page page-width"><a class="back-link" href="/">← LODEX home</a><header class="legal-hero"><p class="eyebrow">Using LODEX</p><h1>${escapeHtml(route.h1)}</h1><p>${escapeHtml(route.intro)}</p></header><div class="legal-content">${(route.paragraphs || []).map((paragraph, index) => `<section><h2>${index === 0 ? 'What this means' : index === 1 ? 'How it applies' : 'Your choices and responsibilities'}</h2><p>${escapeHtml(paragraph)}</p></section>`).join('')}<section><h2>Contact LODEX</h2><p>Questions can be directed to <a href="tel:+14406018001">(440) 601-8001</a>.</p></section></div></article>`
}

function renderBody(route) {
  const content = route.kind === 'home' ? renderHome(route) : route.kind === 'service' ? renderService(route) : renderOther(route)
  return `<main data-lodex-prerendered>${sharedNav()}${content}${sharedFooter()}</main>`
}

function renderDocument(route, body, options = {}) {
  const title = route?.title || `Private workspace | ${SITE_NAME}`
  return template
    .replace(/<title>.*?<\/title>/s, `<title>${escapeHtml(title)}</title>`)
    .replace(/<!-- seo:managed:start -->[\s\S]*?<!-- seo:managed:end -->/, `<!-- seo:managed:start -->\n    ${headFor(route, options)}\n    <!-- seo:managed:end -->`)
    .replace('<div id="app"></div>', `<div id="app">${body}</div>`)
}

async function writeRoute(route) {
  const relative = route.path === '/' ? 'index.html' : `${route.path.slice(1)}.html`
  const output = join(distDir.pathname, relative)
  await mkdir(dirname(output), { recursive: true })
  const document = renderDocument(route, renderBody(route))
  await writeFile(output, document)
}

for (const route of PUBLIC_ROUTES) await writeRoute(route)

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${PUBLIC_ROUTES.map(route => `  <url><loc>${SITE_URL}${route.path === '/' ? '/' : route.path}</loc></url>`).join('\n')}\n</urlset>\n`
await writeFile(new URL('sitemap.xml', distDir), sitemap)

const privateShell = renderDocument(null, '', { noindex: true })
await writeFile(new URL('private-shell.html', distDir), privateShell)
await writeFile(new URL('admin.html', distDir), privateShell)

const notFoundRoute = { title: `Page not found | ${SITE_NAME}`, description: 'The requested LODEX page could not be found.' }
let notFound = renderDocument(notFoundRoute, `${sharedNav()}<main class="legal-page page-width"><header class="legal-hero"><p class="eyebrow">404</p><h1>Page not found</h1><p>The page may have moved or the address may be incorrect.</p><a class="primary-button" href="/">Return to LODEX home</a></header></main>`, { noindex: true })
notFound = notFound.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '').replace(/<script\b[^>]*\/>/gi, '')
await writeFile(new URL('404.html', distDir), notFound)

for (const route of PUBLIC_ROUTES) {
  const output = route.path === '/' ? new URL('index.html', distDir) : new URL(`${route.path.slice(1)}.html`, distDir)
  const html = await readFile(output, 'utf8')
  const h1Count = (html.match(/<h1\b/g) || []).length
  if (h1Count !== 1) throw new Error(`${route.path} contains ${h1Count} pre-rendered H1 elements`)
  const canonical = `${SITE_URL}${route.path === '/' ? '/' : route.path}`
  if (!html.includes(`<link rel="canonical" href="${canonical}"`)) throw new Error(`${route.path} is missing its canonical URL`)
}

// VitePWA calculates the index.html revision before this post-build renderer
// adds route content. Keep the precache revision tied to the final homepage so
// installed clients cannot retain stale pre-rendered HTML.
const finalIndex = await readFile(new URL('index.html', distDir), 'utf8')
const swUrl = new URL('sw.js', distDir)
const serviceWorker = await readFile(swUrl, 'utf8')
if (serviceWorker.includes('NavigationRoute')) throw new Error('The service worker still contains a catch-all navigation fallback')
const indexRevision = createHash('md5').update(finalIndex).digest('hex')
const revisedServiceWorker = serviceWorker.replace(
  /(url:"index\.html",revision:")[^"]+/,
  `$1${indexRevision}`,
)
if (revisedServiceWorker === serviceWorker) throw new Error('Could not update the pre-rendered index.html precache revision')
await writeFile(swUrl, revisedServiceWorker)

console.log(`Pre-rendered ${PUBLIC_ROUTES.length} public routes plus private and 404 shells.`)
