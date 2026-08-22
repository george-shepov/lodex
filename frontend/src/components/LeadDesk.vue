<script setup>
import { computed, onMounted, ref } from 'vue'

const leads = ref([])
const counts = ref({ total: 0, due: 0, open: 0, quoted: 0, won: 0 })
const loading = ref(true)
const error = ref('')
const filter = ref('open')
const showAdd = ref(false)
const showImport = ref(false)
const importText = ref('')
const form = ref({ name: '', service: '', summary: '', reply_to: '', source_url: '', quoted_amount: '', notes: '' })

const filteredLeads = computed(() => {
  if (filter.value === 'all') return leads.value
  if (filter.value === 'due') return leads.value.filter(lead => lead.due_state === 'due')
  if (filter.value === 'won') return leads.value.filter(lead => lead.status === 'won')
  if (filter.value === 'closed') return leads.value.filter(lead => ['lost', 'cold'].includes(lead.status))
  return leads.value.filter(lead => !['won', 'lost', 'cold'].includes(lead.status))
})

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  const raw = await response.text()
  let data = {}
  try { data = raw ? JSON.parse(raw) : {} } catch {}
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status}).`)
  return data
}

async function loadLeads() {
  try {
    const data = await api('/api/admin/leads')
    leads.value = data.leads || []
    counts.value = data.counts || counts.value
    error.value = ''
  } catch (loadError) {
    error.value = loadError.message
  } finally {
    loading.value = false
  }
}

async function createLead() {
  const amount = String(form.value.quoted_amount || '').trim()
  const payload = {
    source: 'yelp',
    name: form.value.name.trim(),
    service: form.value.service.trim() || 'General inquiry',
    summary: form.value.summary.trim(),
    reply_to: form.value.reply_to.trim(),
    source_url: form.value.source_url.trim(),
    quoted_amount_cents: amount ? Math.round(Number(amount) * 100) : null,
    notes: form.value.notes.trim(),
  }
  try {
    await api('/api/admin/leads', { method: 'POST', body: JSON.stringify(payload) })
    form.value = { name: '', service: '', summary: '', reply_to: '', source_url: '', quoted_amount: '', notes: '' }
    showAdd.value = false
    await loadLeads()
  } catch (createError) {
    error.value = createError.message
  }
}

async function updateLead(lead, changes) {
  try {
    await api(`/api/admin/leads/${encodeURIComponent(lead.id)}`, { method: 'PATCH', body: JSON.stringify(changes) })
    await loadLeads()
  } catch (updateError) {
    error.value = updateError.message
  }
}

async function markFollowUp(lead) {
  try {
    await api(`/api/admin/leads/${encodeURIComponent(lead.id)}/follow-up`, { method: 'POST' })
    await loadLeads()
  } catch (followError) {
    error.value = followError.message
  }
}

async function importLeads() {
  try {
    const parsed = JSON.parse(importText.value)
    const payload = Array.isArray(parsed) ? { leads: parsed } : parsed
    const result = await api('/api/admin/leads/import', { method: 'POST', body: JSON.stringify(payload) })
    importText.value = ''
    showImport.value = false
    error.value = `Imported ${result.imported}; ${result.duplicates} duplicate${result.duplicates === 1 ? '' : 's'} skipped.`
    await loadLeads()
  } catch (importError) {
    error.value = importError.message
  }
}

function formatDate(value) {
  if (!value) return 'Not scheduled'
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function formatMoney(cents) {
  if (!Number.isInteger(cents) || cents <= 0) return 'No quote yet'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100)
}

function replyHref(lead) {
  if (!lead.reply_to) return ''
  const subject = encodeURIComponent(`LODEX follow-up: ${lead.service || 'your project'}`)
  return `mailto:${lead.reply_to}?subject=${subject}`
}

onMounted(loadLeads)
</script>

<template>
  <section class="lead-desk">
    <div class="lead-heading">
      <div>
        <p class="eyebrow">Sales pipeline</p>
        <h2>Yelp leads & follow-ups</h2>
        <p>Keep every lead alive until it is won, declined, or the follow-up sequence is exhausted.</p>
      </div>
      <div class="lead-actions">
        <button class="outline-button" type="button" @click="showImport = !showImport">Import</button>
        <button class="primary-button" type="button" @click="showAdd = !showAdd">Add lead</button>
      </div>
    </div>

    <div class="lead-metrics">
      <button type="button" @click="filter = 'due'"><span>Follow up now</span><b>{{ counts.due || 0 }}</b></button>
      <button type="button" @click="filter = 'open'"><span>Open</span><b>{{ counts.open || 0 }}</b></button>
      <button type="button" @click="filter = 'all'"><span>All leads</span><b>{{ counts.total || 0 }}</b></button>
      <button type="button" @click="filter = 'won'"><span>Won</span><b>{{ counts.won || 0 }}</b></button>
    </div>

    <form v-if="showAdd" class="lead-form" @submit.prevent="createLead">
      <label>Customer<input v-model="form.name" required placeholder="Ann M." /></label>
      <label>Service<input v-model="form.service" placeholder="Pressure washing" /></label>
      <label>Yelp reply email<input v-model="form.reply_to" type="email" placeholder="reply+…@messaging.yelp.com" /></label>
      <label>Quoted price<input v-model="form.quoted_amount" inputmode="decimal" placeholder="325" /></label>
      <label class="wide">What they need<textarea v-model="form.summary" rows="3" placeholder="House + garage exterior wash…"></textarea></label>
      <label class="wide">Notes<textarea v-model="form.notes" rows="2" placeholder="Photos received, prefers weekday…"></textarea></label>
      <div class="wide form-actions"><button class="primary-button" type="submit">Save lead</button><button class="outline-button" type="button" @click="showAdd = false">Cancel</button></div>
    </form>

    <div v-if="showImport" class="lead-import">
      <p>Paste a JSON array of Yelp leads. Existing records are deduplicated by <code>source + external_id</code>.</p>
      <textarea v-model="importText" rows="8" placeholder='[{"source":"yelp","external_id":"gmail-message-id","name":"Ann M.","service":"Pressure washing"}]'></textarea>
      <div class="form-actions"><button class="primary-button" type="button" @click="importLeads">Import leads</button><button class="outline-button" type="button" @click="showImport = false">Cancel</button></div>
    </div>

    <p v-if="error" class="lead-message">{{ error }}</p>
    <p v-if="loading" class="lead-empty">Loading leads…</p>
    <p v-else-if="!filteredLeads.length" class="lead-empty">No leads in this view yet.</p>

    <div v-else class="lead-list">
      <article v-for="lead in filteredLeads" :key="lead.id" :class="['lead-card', `due-${lead.due_state}`]">
        <div class="lead-card-top">
          <div><span>{{ lead.source || 'lead' }} · {{ lead.status }}</span><h3>{{ lead.name }} · {{ lead.service }}</h3></div>
          <b>{{ formatMoney(lead.quoted_amount_cents) }}</b>
        </div>
        <p v-if="lead.summary">{{ lead.summary }}</p>
        <p v-if="lead.notes" class="lead-notes">{{ lead.notes }}</p>
        <div class="lead-meta">
          <span><b>Next follow-up</b>{{ formatDate(lead.next_follow_up_at) }}</span>
          <span><b>Touches</b>{{ lead.follow_up_count || 0 }}</span>
          <span><b>Last contact</b>{{ formatDate(lead.last_contact_at) }}</span>
        </div>
        <div class="lead-card-actions">
          <a v-if="lead.reply_to" class="primary-button" :href="replyHref(lead)">Reply</a>
          <button v-if="!['won','lost','cold'].includes(lead.status)" class="outline-button" type="button" @click="markFollowUp(lead)">Followed up</button>
          <select :value="lead.status" @change="updateLead(lead, { status: $event.target.value })">
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="waiting">Waiting</option>
            <option value="quoted">Quoted</option>
            <option value="follow_up">Follow-up</option>
            <option value="scheduled">Scheduled</option>
            <option value="won">Won</option>
            <option value="lost">Lost</option>
            <option value="cold">Cold</option>
          </select>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.lead-desk { margin: 24px 0; padding: 22px; border: 1px solid rgba(210,162,84,.34); border-radius: 18px; background: #0d181a; color: #f3eee4; }
.lead-heading, .lead-card-top, .lead-card-actions, .lead-actions, .form-actions { display: flex; gap: 12px; align-items: center; justify-content: space-between; }
.lead-heading h2 { margin: 4px 0 6px; }
.lead-heading p { margin: 0; color: #aab8b8; }
.lead-metrics { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; margin: 18px 0; }
.lead-metrics button { text-align: left; border: 1px solid #284144; border-radius: 12px; padding: 12px; background: #112225; color: inherit; }
.lead-metrics span, .lead-meta b { display: block; color: #91a5a5; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }
.lead-metrics b { display: block; margin-top: 4px; font-size: 24px; color: #edc57b; }
.lead-form { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; margin: 14px 0; padding: 16px; border-radius: 14px; background: #112225; }
.lead-form label { display: grid; gap: 6px; font-size: 12px; color: #b9c5c5; }
.lead-form input, .lead-form textarea, .lead-import textarea, select { width: 100%; box-sizing: border-box; border: 1px solid #355155; border-radius: 9px; background: #0a1517; color: #f3eee4; padding: 10px; }
.wide { grid-column: 1 / -1; }
.lead-import { margin: 14px 0; padding: 16px; border-radius: 14px; background: #112225; }
.lead-import textarea { margin: 8px 0 12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.lead-list { display: grid; gap: 12px; }
.lead-card { border: 1px solid #294247; border-radius: 14px; padding: 15px; background: #101f22; }
.lead-card.due-due { border-color: #d2a254; box-shadow: inset 4px 0 0 #d2a254; }
.lead-card-top span { color: #88a0a0; font-size: 11px; text-transform: uppercase; }
.lead-card-top h3 { margin: 4px 0; }
.lead-card-top > b { color: #edc57b; }
.lead-card > p { color: #c4cece; }
.lead-notes { font-size: 13px; color: #9fb0b0 !important; }
.lead-meta { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 10px; margin: 12px 0; }
.lead-meta span { padding: 9px; border-radius: 9px; background: #0b1719; font-size: 12px; }
.lead-card-actions { justify-content: flex-start; flex-wrap: wrap; }
.lead-card-actions select { width: auto; min-width: 130px; }
.lead-message { padding: 10px 12px; border-radius: 9px; background: #16282b; color: #edc57b; }
.lead-empty { color: #91a5a5; }
.primary-button, .outline-button { text-decoration: none; }
@media (max-width: 720px) {
  .lead-heading { align-items: flex-start; flex-direction: column; }
  .lead-metrics { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .lead-form { grid-template-columns: 1fr; }
  .wide { grid-column: auto; }
  .lead-meta { grid-template-columns: 1fr; }
  .lead-card-top { align-items: flex-start; flex-direction: column; }
}
</style>
