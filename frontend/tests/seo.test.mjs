import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import {
  canonicalForPath,
  PUBLIC_ROUTES,
  SERVICE_ROUTES,
  SITE_URL,
  structuredDataForRoute,
} from '../src/seo.mjs'
import { SMS_COMPLIANCE, smsComplianceForPath } from '../src/smsCompliance.mjs'
import { PHONE_INPUT_SELECTOR, SMS_CONSENT_TEXT, SMS_CONSENT_VERSION } from '../src/smsConsent.mjs'

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
assert.match(appSource, /type="tel"/)
assert.match(appSource, /placeholder="Phone"/)

const privacySms = smsComplianceForPath('/privacy')
const termsSms = smsComplianceForPath('/terms/')
assert.equal(privacySms, SMS_COMPLIANCE['/privacy'])
assert.equal(termsSms, SMS_COMPLIANCE['/terms'])
assert.match(privacySms.paragraphs.join(' '), /does not sell, rent, share, or provide mobile phone numbers/i)
assert.match(privacySms.paragraphs.join(' '), /message and data rates may apply/i)
assert.match(privacySms.paragraphs.join(' '), /Reply STOP to opt out or HELP for assistance/i)
assert.match(termsSms.paragraphs.join(' '), /Consent to receive text messages is not a condition of purchasing services/i)
assert.match(termsSms.paragraphs.join(' '), /replying STOP/i)
assert.match(termsSms.paragraphs.join(' '), /Reply HELP for assistance/i)

assert.equal(SMS_CONSENT_VERSION, '2026-09-13-v1')
assert.match(SMS_CONSENT_TEXT, /service-related SMS\/MMS messages from LODEX/i)
assert.match(SMS_CONSENT_TEXT, /Message frequency varies/i)
assert.match(SMS_CONSENT_TEXT, /Message and data rates may apply/i)
assert.match(SMS_CONSENT_TEXT, /Reply STOP to opt out or HELP for assistance/i)
assert.match(SMS_CONSENT_TEXT, /Consent is not a condition of purchase/i)
assert.match(PHONE_INPUT_SELECTOR, /input\[type="tel"\]/)
assert.match(PHONE_INPUT_SELECTOR, /autocomplete="tel"/)
assert.match(PHONE_INPUT_SELECTOR, /placeholder\*="phone" i/)

const consentSource = await readFile(new URL('../src/smsConsent.mjs', import.meta.url), 'utf8')
assert.match(consentSource, /checkbox\.checked = false/)
assert.match(consentSource, /checkbox\.required = false/)
assert.match(consentSource, /new MutationObserverClass/)
assert.match(consentSource, /createLink\(documentRef, '\/privacy'/)
assert.match(consentSource, /createLink\(documentRef, '\/terms'/)
assert.match(consentSource, /fetch\('\/api\/sms\/consent'/)
assert.match(consentSource, /keepalive: true/)
assert.match(consentSource, /consent: true/)
assert.match(consentSource, /consent_text: SMS_CONSENT_TEXT/)
assert.match(consentSource, /consent_version: SMS_CONSENT_VERSION/)
assert.match(consentSource, /addEventListener\('submit', handleSubmit, true\)/)

const mainSource = await readFile(new URL('../src/main.js', import.meta.url), 'utf8')
assert.match(mainSource, /installSmsConsent\(document\)/)
assert.match(mainSource, /installSmsCompliance\(document, window\.location\.pathname\)/)
assert.match(mainSource, /import '\.\/smsConsent\.css'/)

const prerenderSource = await readFile(new URL('../scripts/prerender.mjs', import.meta.url), 'utf8')
assert.match(prerenderSource, /data-sms-compliance/)
assert.match(prerenderSource, /smsComplianceForPath\(route\.path\)/)

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

console.log('SEO route, sitemap, crawler, canonical, SMS compliance, consent, and audit checks passed')
