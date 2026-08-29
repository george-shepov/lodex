<script setup>
import { onMounted, ref } from 'vue'

const concepts = ref([])
const loading = ref(true)
const error = ref('')
const showCreate = ref(false)
const saving = ref(false)
const form = ref(freshForm())

function freshOffer(index) {
  return {
    retailer_key: 'manual-catalog', retailer_name: 'Manual catalog', retailer_homepage_url: '', retailer_terms_notes: 'Manually entered from an approved catalog.',
    retailer_product_id: `product-${index}`, brand: '', product_name: '', product_url: '', image_url: '', product_category: '', sku: '', regular_price: '', availability_status: 'UNKNOWN', source_timestamp: new Date().toISOString(),
  }
}

function freshComponent(index, group = index === 1 ? 'structure / construction' : 'furniture') {
  return { group, name: '', description: '', quantity: '1', unit: 'each', selection_mode: 'SUBSTITUTE_ALLOWED', requirement_spec: '{}', offer: freshOffer(index) }
}

function freshForm() {
  return {
    name: '', slug: '', category: 'Backyard Offices', summary: '', description: '', status: 'CONCEPT', publication_status: 'DRAFT',
    width: '', length: '', height: '', dimension_unit: 'ft', hero_url: '', hero_alt: '', intended_use: '', features: '', options: '',
    labor: '', overhead: '', lead_min: 30, lead_max: 60, validity: 72, markup_method: 'PERCENT', markup_value: '25',
    components: [freshComponent(1), freshComponent(2, 'electrical / lighting')],
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status}).`)
  return data
}

async function loadConcepts() {
  try {
    concepts.value = (await api('/api/admin/concepts')).concepts || []
    error.value = ''
  } catch (loadError) {
    error.value = loadError.message
  } finally {
    loading.value = false
  }
}

function cents(value) {
  const amount = Number(value || 0)
  return Number.isFinite(amount) ? Math.round(amount * 100) : 0
}

function money(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format((value || 0) / 100)
}

function splitLines(value) {
  return String(value || '').split('\n').map(item => item.trim()).filter(Boolean)
}

async function createConcept() {
  saving.value = true
  error.value = ''
  try {
    const payload = {
      slug: form.value.slug, name: form.value.name, category: form.value.category, summary: form.value.summary, description: form.value.description,
      status: form.value.status, publication_status: form.value.publication_status, width: form.value.width || null, length: form.value.length || null, height: form.value.height || null,
      dimension_unit: form.value.dimension_unit, hero_media: form.value.hero_url ? { url: form.value.hero_url, alt: form.value.hero_alt || `${form.value.name} concept design` } : {},
      intended_use: form.value.intended_use, included_features: splitLines(form.value.features), configurable_options: splitLines(form.value.options), commercial_modes: ['DESIGN_ONLY', 'BUILD_ONLY', 'TURNKEY'],
      base_labor_estimate_cents: cents(form.value.labor), base_project_overhead_cents: cents(form.value.overhead), lead_time_min_days: Number(form.value.lead_min), lead_time_max_days: Number(form.value.lead_max), price_validity_hours: Number(form.value.validity),
      markup_policy: { name: `${form.value.name} markup`, scope: 'CONCEPT', method: form.value.markup_method, value: form.value.markup_method === 'FIXED' ? String(cents(form.value.markup_value)) : String(form.value.markup_value), minimum_margin_amount_cents: 0 },
      components: form.value.components.map((component, index) => ({
        group: component.group, name: component.name, description: component.description, quantity: component.quantity, unit: component.unit, selection_mode: component.selection_mode, required: true, sort_order: (index + 1) * 10,
        requirement_spec_json: JSON.parse(component.requirement_spec || '{}'),
        offer: { ...component.offer, regular_price_cents: cents(component.offer.regular_price), currency: 'USD', attributes_json: {}, fulfillment_json: {}, raw_source_ref: 'admin-manual-entry' },
      })),
    }
    await api('/api/admin/concepts', { method: 'POST', body: JSON.stringify(payload) })
    form.value = freshForm()
    showCreate.value = false
    await loadConcepts()
  } catch (createError) {
    error.value = createError instanceof SyntaxError ? 'Each component requirement must be valid JSON.' : createError.message
  } finally {
    saving.value = false
  }
}

function addComponent() {
  form.value.components.push(freshComponent(form.value.components.length + 1))
}

function slugFromName() {
  if (!form.value.slug) form.value.slug = form.value.name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

onMounted(loadConcepts)
</script>

<template>
  <section class="catalog-admin">
    <header><div><p class="eyebrow">Design commerce</p><h2>Concept catalog</h2><p>Build sellable specifications from replaceable manual catalog offers.</p></div><button class="primary-button" type="button" @click="showCreate = !showCreate">{{ showCreate ? 'Close editor' : 'New concept' }}</button></header>
    <p v-if="error" class="catalog-message">{{ error }}</p>
    <form v-if="showCreate" class="concept-form" @submit.prevent="createConcept">
      <div class="form-section"><h3>Concept</h3><div class="form-grid"><label>Name<input v-model="form.name" required @blur="slugFromName" /></label><label>Slug<input v-model="form.slug" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></label><label>Category<input v-model="form.category" required /></label><label>Status<select v-model="form.status"><option>CONCEPT</option><option>BUILT_PROJECT</option><option>RETIRED</option></select></label><label>Publication<select v-model="form.publication_status"><option>DRAFT</option><option>PUBLISHED</option><option>ARCHIVED</option></select></label><label>Hero image URL<input v-model="form.hero_url" placeholder="/inspiration/..." /></label><label class="wide">Summary<input v-model="form.summary" required /></label><label class="wide">Description<textarea v-model="form.description" rows="3"></textarea></label><label class="wide">Intended use<textarea v-model="form.intended_use" rows="2"></textarea></label><label>Width<input v-model="form.width" /></label><label>Length<input v-model="form.length" /></label><label>Height<input v-model="form.height" /></label><label>Unit<input v-model="form.dimension_unit" /></label><label class="wide">Included features, one per line<textarea v-model="form.features" rows="3"></textarea></label><label class="wide">Options, one per line<textarea v-model="form.options" rows="3"></textarea></label></div></div>
      <div class="form-section"><h3>Internal pricing</h3><div class="form-grid"><label>Labor ($)<input v-model="form.labor" inputmode="decimal" required /></label><label>Project overhead ($)<input v-model="form.overhead" inputmode="decimal" required /></label><label>Markup method<select v-model="form.markup_method"><option value="PERCENT">Percent</option><option value="FIXED">Fixed amount</option></select></label><label>{{ form.markup_method === 'PERCENT' ? 'Markup (%)' : 'Markup ($)' }}<input v-model="form.markup_value" inputmode="decimal" required /></label><label>Lead time min (days)<input v-model.number="form.lead_min" type="number" min="1" required /></label><label>Lead time max (days)<input v-model.number="form.lead_max" type="number" min="1" required /></label><label>Price validity (hours)<input v-model.number="form.validity" type="number" min="1" required /></label></div></div>
      <div class="form-section"><div class="component-heading"><h3>Components and manual offers</h3><button type="button" class="outline-button" @click="addComponent">Add component</button></div><article v-for="(component, index) in form.components" :key="index" class="component-editor"><b>Component {{ index + 1 }}</b><div class="form-grid"><label>Group<input v-model="component.group" required /></label><label>Requirement name<input v-model="component.name" required /></label><label>Quantity<input v-model="component.quantity" required /></label><label>Unit<input v-model="component.unit" required /></label><label class="wide">Requirement JSON<textarea v-model="component.requirement_spec" rows="3" required></textarea></label><label>Retailer key<input v-model="component.offer.retailer_key" required /></label><label>Retailer name<input v-model="component.offer.retailer_name" required /></label><label>Retailer homepage<input v-model="component.offer.retailer_homepage_url" type="url" /></label><label>Retailer product ID<input v-model="component.offer.retailer_product_id" required /></label><label>Brand<input v-model="component.offer.brand" /></label><label>Product name<input v-model="component.offer.product_name" required /></label><label>Product URL<input v-model="component.offer.product_url" type="url" /></label><label>SKU<input v-model="component.offer.sku" /></label><label>Acquisition price ($)<input v-model="component.offer.regular_price" inputmode="decimal" required /></label><label>Availability<select v-model="component.offer.availability_status"><option>IN_STOCK</option><option>LOW_STOCK</option><option>OUT_OF_STOCK</option><option>UNKNOWN</option></select></label></div></article></div>
      <button class="primary-button save-concept" type="submit" :disabled="saving">{{ saving ? 'Saving concept…' : 'Save concept' }}</button>
    </form>
    <p v-if="loading" class="catalog-empty">Loading concepts…</p><p v-else-if="!concepts.length" class="catalog-empty">No concepts yet. Create the first draft above.</p>
    <div v-else class="concept-list"><article v-for="item in concepts" :key="item.concept.id"><div><span>{{ item.concept.status }} · {{ item.concept.publication_status }}</span><h3>{{ item.concept.name }}</h3><p>{{ item.concept.category }} · {{ item.components.length }} components</p></div><dl><div><dt>Acquisition</dt><dd>{{ money(item.pricing.acquisition_subtotal_cents) }}</dd></div><div><dt>LODEX markup</dt><dd>{{ money(item.pricing.procurement_markup_cents) }}</dd></div><div><dt>Labor + overhead</dt><dd>{{ money(item.pricing.labor_cents + item.pricing.project_overhead_cents) }}</dd></div><div class="customer-total"><dt>Customer turnkey</dt><dd>{{ money(item.pricing.total_cents) }}</dd></div></dl><a v-if="item.concept.publication_status === 'PUBLISHED'" :href="`/designs/${encodeURIComponent(item.concept.category.toLowerCase().replaceAll(' ', '-'))}/${item.concept.slug}`">Open public concept ↗</a></article></div>
  </section>
</template>

<style scoped>
.catalog-admin { margin: 24px 0; padding: 22px; border: 1px solid #2c474a; background: #0d181a; color: #f3eee4; }
.catalog-admin > header, .component-heading { display: flex; justify-content: space-between; align-items: center; gap: 18px; }
.catalog-admin header h2 { margin: 4px 0; }
.catalog-admin header p { margin: 0; color: #9eafaf; }
.catalog-message { padding: 11px; background: #3d2521; color: #ffd7c8; }
.concept-form { display: grid; gap: 16px; margin: 20px 0; }
.form-section, .concept-list article { padding: 18px; border: 1px solid #294347; background: #112225; }
.form-section h3 { margin-top: 0; color: #edc57b; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }
.form-grid label { display: grid; gap: 6px; color: #b8c5c4; font-size: 12px; }
.form-grid input, .form-grid textarea, .form-grid select { box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid #3b585c; border-radius: 4px; background: #091416; color: white; }
.form-grid .wide { grid-column: 1 / -1; }
.component-editor { margin-top: 15px; padding: 15px; border-left: 3px solid #d2a254; background: #0b191b; }
.component-editor > b { display: block; margin-bottom: 13px; }
.save-concept { justify-self: end; }
.concept-list { display: grid; gap: 12px; }
.concept-list article { display: grid; grid-template-columns: 1fr 1.2fr auto; gap: 24px; align-items: center; }
.concept-list span { color: #8fa2a2; font-size: 11px; }
.concept-list h3 { margin: 5px 0; }
.concept-list p { margin: 0; color: #aab9b8; }
.concept-list dl { display: grid; grid-template-columns: repeat(4,1fr); margin: 0; }
.concept-list dl div { padding: 8px; border-left: 1px solid #2a4548; }
.concept-list dt { color: #8fa2a2; font-size: 10px; text-transform: uppercase; }
.concept-list dd { margin: 4px 0 0; font-weight: 800; }
.concept-list .customer-total dd { color: #edc57b; }
.concept-list a { color: #edc57b; white-space: nowrap; }
.catalog-empty { padding: 20px; text-align: center; color: #91a5a5; }
@media (max-width: 900px) { .concept-list article { grid-template-columns: 1fr; } .concept-list dl { grid-template-columns: repeat(2,1fr); } }
@media (max-width: 650px) { .catalog-admin > header, .component-heading { align-items: flex-start; flex-direction: column; } .form-grid { grid-template-columns: 1fr; } .form-grid .wide { grid-column: auto; } }
</style>