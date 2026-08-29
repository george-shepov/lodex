<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({ slug: { type: String, required: true } })
const emit = defineEmits(['back', 'start'])

const concept = ref(null)
const loading = ref(true)
const error = ref('')
const quote = ref(null)
const quoteLoading = ref(false)

const groups = computed(() => {
  const grouped = new Map()
  for (const component of concept.value?.component_groups || []) {
    const key = component.group || 'Included items'
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key).push(component)
  }
  return [...grouped.entries()].map(([name, components]) => ({ name, components }))
})

function money(cents) {
  if (!Number.isInteger(cents)) return 'Price under review'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(cents / 100)
}

function modeLabel(mode) {
  return { DESIGN_ONLY: 'Design Only', BUILD_ONLY: 'Build Only', TURNKEY: 'Turnkey / Move-In Ready' }[mode] || mode
}

function sourceDate(value) {
  if (!value) return 'Availability being verified'
  return `Availability checked ${new Intl.DateTimeFormat('en-US', { dateStyle: 'medium' }).format(new Date(value))}`
}

function dimensions(value) {
  if (!value) return 'Sized to your site'
  const parts = [value.width, value.length, value.height].filter(Boolean)
  return parts.length ? `${parts.join(' × ')} ${value.unit || ''}`.trim() : 'Sized to your site'
}

async function loadConcept() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch(`/api/concepts/${encodeURIComponent(props.slug)}`)
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'This concept is not available.')
    concept.value = data
    document.title = `${data.name} | LODEX ${data.status_label}`
    document.querySelector('meta[name="description"]')?.setAttribute('content', data.summary)
  } catch (loadError) {
    error.value = loadError.message
  } finally {
    loading.value = false
  }
}

async function lockQuote() {
  if (!concept.value || quoteLoading.value) return
  quoteLoading.value = true
  error.value = ''
  try {
    const response = await fetch(`/api/concepts/${encodeURIComponent(concept.value.id)}/quote-request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'The quote could not be created.')
    quote.value = data
  } catch (quoteError) {
    error.value = quoteError.message
  } finally {
    quoteLoading.value = false
  }
}

watch(() => props.slug, loadConcept)
onMounted(loadConcept)
</script>

<template>
  <div class="concept-page">
    <div v-if="loading" class="concept-state">Loading design details…</div>
    <div v-else-if="error && !concept" class="concept-state"><p>{{ error }}</p><button type="button" @click="emit('back')">Return to inspiration</button></div>
    <template v-else-if="concept">
      <section class="concept-hero">
        <img v-if="concept.hero_media?.url" :src="concept.hero_media.url" :alt="concept.hero_media.alt || `${concept.name} concept design`" />
        <div class="concept-hero-scrim"></div>
        <button class="concept-back" type="button" @click="emit('back')">← Inspiration</button>
        <div class="concept-hero-copy">
          <span class="concept-badge">{{ concept.status_label }}</span>
          <p>{{ concept.category }}</p>
          <h1>{{ concept.name }}</h1>
          <b>{{ concept.summary }}</b>
        </div>
      </section>

      <section class="concept-summary page-width">
        <div class="concept-overview">
          <p class="eyebrow">Sellable design specification</p>
          <h2>Designed as a complete outcome.</h2>
          <p>{{ concept.description }}</p>
          <dl>
            <div><dt>Approximate dimensions</dt><dd>{{ dimensions(concept.dimensions) }}</dd></div>
            <div><dt>Intended use</dt><dd>{{ concept.intended_use || 'Configured around your site and intended use.' }}</dd></div>
            <div><dt>Estimated lead time</dt><dd>{{ concept.lead_time.min_days }}–{{ concept.lead_time.max_days }} days</dd></div>
          </dl>
        </div>
        <aside class="concept-commercial">
          <span>Preliminary turnkey price</span>
          <strong>{{ money(concept.price.turnkey_price_cents) }}</strong>
          <small>{{ sourceDate(concept.price.availability_as_of) }}</small>
          <p>{{ concept.availability_caveat }} {{ concept.substitution_policy }}</p>
          <div class="concept-modes"><span v-for="mode in concept.commercial_modes" :key="mode">{{ modeLabel(mode) }}</span></div>
          <button class="primary-button" type="button" @click="lockQuote" :disabled="quoteLoading">{{ quoteLoading ? 'Locking assumptions…' : 'Build this design' }} <span>↗</span></button>
          <button class="outline-button" type="button" @click="emit('start', concept)">Customize this concept</button>
          <div v-if="quote" class="quote-confirmation"><b>Preliminary quote {{ quote.quote_id }}</b><span>{{ money(quote.total_cents) }} · valid until {{ new Date(quote.valid_until).toLocaleString() }}</span><small>Selections and pricing are frozen in this quote. Substitutions follow the policy shown above.</small></div>
          <p v-if="error" class="concept-error">{{ error }}</p>
        </aside>
      </section>

      <section class="concept-details page-width">
        <div>
          <p class="eyebrow">Included features</p>
          <h2>What shapes the design.</h2>
          <ul><li v-for="feature in concept.included_features" :key="feature">{{ feature }}</li></ul>
        </div>
        <div>
          <p class="eyebrow">Configurable options</p>
          <h2>Where it can become yours.</h2>
          <ul><li v-for="option in concept.configurable_options" :key="option">{{ option }}</li></ul>
        </div>
      </section>

      <section class="concept-components">
        <div class="page-width">
          <div class="concept-section-heading"><p class="eyebrow">Products and materials</p><h2>Organized around the finished space.</h2><p>Named products are current fulfillment options, not permanent dependencies. Equivalent substitutions may be proposed when stock or pricing changes.</p></div>
          <div class="component-groups">
            <article v-for="group in groups" :key="group.name">
              <h3>{{ group.name }}</h3>
              <div v-for="component in group.components" :key="component.name" class="component-row">
                <div><b>{{ component.name }}</b><span>{{ component.quantity }} {{ component.unit }}</span></div>
                <div><span>{{ component.product.brand }} {{ component.product.name }}</span><small>{{ component.product.availability_status.replaceAll('_', ' ').toLowerCase() }} · {{ sourceDate(component.product.source_timestamp) }}</small></div>
              </div>
            </article>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.concept-page { background: #f3f0e8; color: #182426; min-height: 80vh; }
.concept-state { min-height: 65vh; display: grid; place-content: center; gap: 16px; text-align: center; }
.concept-state button { border: 0; background: #182426; color: white; padding: 12px 18px; }
.concept-hero { position: relative; min-height: min(72vh, 760px); display: flex; align-items: flex-end; overflow: hidden; background: #213538; color: white; }
.concept-hero > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.concept-hero-scrim { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(11,22,24,.1) 15%, rgba(11,22,24,.86) 100%); }
.concept-back { position: absolute; z-index: 2; top: 30px; left: clamp(20px, 5vw, 80px); border: 1px solid rgba(255,255,255,.55); background: rgba(17,29,31,.75); color: white; padding: 10px 14px; }
.concept-hero-copy { position: relative; z-index: 1; width: min(1180px, calc(100% - 40px)); margin: 0 auto; padding: 60px 0; }
.concept-hero-copy p, .concept-commercial > span { text-transform: uppercase; font: 700 12px/1.2 'Space Grotesk', sans-serif; letter-spacing: 0; }
.concept-hero-copy h1 { max-width: 900px; margin: 9px 0 12px; font: 500 clamp(44px, 8vw, 104px)/.9 'DM Sans', sans-serif; letter-spacing: 0; }
.concept-hero-copy > b { display: block; max-width: 680px; font-size: clamp(17px, 2vw, 24px); line-height: 1.45; }
.concept-badge { display: inline-block; padding: 7px 10px; background: #f0bd50; color: #152326; font-size: 11px; font-weight: 900; text-transform: uppercase; }
.concept-summary { display: grid; grid-template-columns: 1.3fr .7fr; gap: clamp(40px, 7vw, 110px); padding-top: 80px; padding-bottom: 80px; }
.concept-overview h2, .concept-details h2, .concept-section-heading h2 { margin: 8px 0 18px; font-size: clamp(32px, 4vw, 55px); line-height: 1; }
.concept-overview > p { font-size: 18px; line-height: 1.7; color: #435255; }
.concept-overview dl { display: grid; gap: 0; margin-top: 38px; }
.concept-overview dl div { display: grid; grid-template-columns: 190px 1fr; gap: 20px; padding: 16px 0; border-top: 1px solid #b9beb7; }
.concept-overview dt { font-size: 12px; font-weight: 800; text-transform: uppercase; }
.concept-overview dd { margin: 0; }
.concept-commercial { align-self: start; padding: 28px; border-top: 5px solid #d39b31; background: #fff; box-shadow: 0 18px 50px rgba(30,40,40,.1); }
.concept-commercial strong { display: block; margin: 8px 0 2px; font-size: 42px; color: #9c6510; }
.concept-commercial > small { color: #657174; }
.concept-commercial > p { font-size: 13px; line-height: 1.55; color: #586568; }
.concept-commercial button { width: 100%; margin-top: 10px; justify-content: center; }
.concept-modes { display: grid; gap: 6px; margin: 18px 0; }
.concept-modes span { padding: 9px 11px; background: #eef0eb; font-size: 12px; font-weight: 800; }
.quote-confirmation { display: grid; gap: 5px; margin-top: 14px; padding: 13px; background: #e5f1e9; color: #214630; }
.quote-confirmation span, .quote-confirmation small { font-size: 12px; }
.concept-error { color: #a6322d !important; }
.concept-details { display: grid; grid-template-columns: 1fr 1fr; gap: 80px; padding-top: 20px; padding-bottom: 80px; }
.concept-details ul { padding: 0; list-style: none; }
.concept-details li { padding: 13px 0; border-bottom: 1px solid #b9beb7; }
.concept-components { padding: 80px 0; background: #132427; color: #eef0e9; }
.concept-section-heading { max-width: 750px; }
.concept-section-heading > p:last-child { color: #aab6b5; line-height: 1.6; }
.component-groups { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 18px; margin-top: 38px; }
.component-groups article { padding: 22px; border: 1px solid #355053; background: #182d30; }
.component-groups h3 { margin: 0 0 18px; text-transform: capitalize; color: #efc36f; }
.component-row { display: grid; grid-template-columns: .8fr 1.2fr; gap: 15px; padding: 14px 0; border-top: 1px solid #345053; }
.component-row div { display: grid; gap: 4px; }
.component-row span, .component-row small { color: #b6c2c1; font-size: 12px; }
@media (max-width: 800px) {
  .concept-hero { min-height: 590px; }
  .concept-summary, .concept-details, .component-groups { grid-template-columns: 1fr; gap: 38px; }
  .concept-overview dl div, .component-row { grid-template-columns: 1fr; gap: 7px; }
  .concept-hero-copy { padding-bottom: 38px; }
  .concept-commercial { padding: 21px; }
}
</style>