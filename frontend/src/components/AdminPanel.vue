<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { APP_VERSION, BUILD_VERSION } from '../buildVersion.js'
import LeadDesk from './LeadDesk.vue'

const emit = defineEmits(['join-room'])

const token = ref('')
const authenticated = ref(false)
const loading = ref(true)
const error = ref('')
const overview = ref({ active_visitors: [], project_requests: [], support_requests: [], counts: {} })
const alertsEnabled = ref(false)
const selectedMedia = ref(null)
const supportPanel = ref(null)
const supportFlash = ref(false)
let eventSocket = null
let refreshTimer = null
let socketPing = null
let audioContext = null
let supportFlashTimer = null
let titleRestoreTimer = null
const normalTitle = document.title

const activeVisitors = computed(() => overview.value.active_visitors || [])
const projectRequests = computed(() => overview.value.project_requests || [])
const supportRequests = computed(() => overview.value.support_requests || [])
const shortBuild = computed(() => String(BUILD_VERSION).split('+').pop()?.slice(-8) || BUILD_VERSION)

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

async function checkSession() {
  loading.value = true
  try {
    await api('/api/admin/session')
    authenticated.value = true
    await startDashboard()
  } catch {
    authenticated.value = false
  } finally {
    loading.value = false
  }
}

async function login() {
  error.value = ''
  try {
    await api('/api/admin/login', { method: 'POST', body: JSON.stringify({ token: token.value }) })
    token.value = ''
    authenticated.value = true
    await startDashboard()
  } catch (loginError) {
    error.value = loginError.message
  }
}

async function logout() {
  try { await api('/api/admin/session', { method: 'DELETE' }) } catch {}
  disconnectEvents()
  authenticated.value = false
  selectedMedia.value = null
  overview.value = { active_visitors: [], project_requests: [], support_requests: [], counts: {} }
}

async function loadOverview() {
  if (!authenticated.value) return
  try {
    overview.value = await api('/api/admin/overview')
    error.value = ''
  } catch (loadError) {
    error.value = loadError.message
    if (/authentication/i.test(loadError.message)) authenticated.value = false
  }
}

function connectEvents() {
  disconnectEvents()
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  eventSocket = new WebSocket(`${protocol}//${window.location.host}/api/admin/events`)
  eventSocket.onmessage = event => {
    const message = JSON.parse(event.data)
    if (['visitor.entered', 'project.created', 'support.requested', 'project.updated'].includes(message.type)) {
      notifyOwner(message)
      loadOverview()
    }
  }
  eventSocket.onclose = () => {
    if (authenticated.value) window.setTimeout(connectEvents, 3000)
  }
  socketPing = window.setInterval(() => {
    if (eventSocket?.readyState === WebSocket.OPEN) eventSocket.send('ping')
  }, 20000)
}

function disconnectEvents() {
  window.clearInterval(socketPing)
  socketPing = null
  if (eventSocket) {
    eventSocket.onclose = null
    eventSocket.close()
  }
  eventSocket = null
}

async function startDashboard() {
  await loadOverview()
  connectEvents()
  window.clearInterval(refreshTimer)
  refreshTimer = window.setInterval(loadOverview, 15000)
}

async function enableAlerts() {
  audioContext ||= new (window.AudioContext || window.webkitAudioContext)()
  if (audioContext.state === 'suspended') await audioContext.resume()
  if ('Notification' in window && Notification.permission === 'default') await Notification.requestPermission()
  alertsEnabled.value = true
  try { localStorage.setItem('lodex-owner-alerts', 'enabled') } catch {}
  beep(740, 0.12)
}

function beep(frequency = 680, duration = 0.18) {
  if (!alertsEnabled.value || !audioContext) return
  const oscillator = audioContext.createOscillator()
  const gain = audioContext.createGain()
  oscillator.frequency.value = frequency
  oscillator.type = 'sine'
  gain.gain.setValueAtTime(0.0001, audioContext.currentTime)
  gain.gain.exponentialRampToValueAtTime(0.16, audioContext.currentTime + 0.02)
  gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + duration)
  oscillator.connect(gain).connect(audioContext.destination)
  oscillator.start()
  oscillator.stop(audioContext.currentTime + duration + 0.02)
}

async function spotlightSupport() {
  supportFlash.value = false
  await nextTick()
  supportFlash.value = true
  supportPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  try { window.focus() } catch {}
  if (navigator.vibrate) navigator.vibrate([220, 100, 220, 100, 500])
  window.clearTimeout(supportFlashTimer)
  supportFlashTimer = window.setTimeout(() => { supportFlash.value = false }, 7000)

  window.clearTimeout(titleRestoreTimer)
  document.title = '🔴 LIVE SUPPORT · LODEX'
  titleRestoreTimer = window.setTimeout(() => { document.title = normalTitle }, 12000)
}

function notifyOwner(event) {
  const titles = {
    'visitor.entered': 'Someone is on LODEX',
    'project.created': 'New LODEX project request',
    'support.requested': 'Live support call requested',
    'project.updated': 'Project status updated',
  }
  const body = event.type === 'visitor.entered'
    ? event.payload.path
    : event.type === 'support.requested'
      ? `${event.payload.name || 'Visitor'} · room ${event.payload.room_code}`
      : `${event.payload.project_code || ''} ${event.payload.service_category || ''}`.trim()

  if (event.type === 'support.requested') spotlightSupport()
  beep(event.type === 'support.requested' ? 920 : 680, event.type === 'support.requested' ? 0.36 : 0.16)
  if (alertsEnabled.value && 'Notification' in window && Notification.permission === 'granted') {
    const notification = new Notification(titles[event.type], {
      body,
      icon: '/lodex-app-icon-192-v2.png',
      tag: event.type === 'visitor.entered' ? 'lodex-visitor' : `${event.type}-${Date.now()}`,
      requireInteraction: event.type === 'support.requested',
    })
    if (event.type === 'support.requested') notification.onclick = () => { window.focus(); spotlightSupport(); notification.close() }
  }
}

async function updateStatus(project, status) {
  try {
    await api(`/api/admin/projects/${encodeURIComponent(project.project_code)}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, note: '' }),
    })
    await loadOverview()
  } catch (statusError) {
    error.value = statusError.message
  }
}

function joinRoom(roomCode) {
  emit('join-room', roomCode)
}

function mediaUrl(file) {
  return `/api/admin/uploads/${encodeURIComponent(file.upload_id)}`
}

function isImage(file) {
  return String(file?.media_type || '').startsWith('image/')
}

function isVideo(file) {
  return String(file?.media_type || '').startsWith('video/')
}

function openMedia(file) {
  selectedMedia.value = file
}

function closeMedia() {
  selectedMedia.value = null
}

function onKeydown(event) {
  if (event.key === 'Escape' && selectedMedia.value) closeMedia()
}

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function formatMoney(cents) {
  if (!Number.isInteger(cents) || cents <= 0) return 'Review required'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100)
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  try { alertsEnabled.value = localStorage.getItem('lodex-owner-alerts') === 'enabled' && Notification?.permission === 'granted' } catch {}
  checkSession()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  disconnectEvents()
  window.clearInterval(refreshTimer)
  window.clearTimeout(supportFlashTimer)
  window.clearTimeout(titleRestoreTimer)
  document.title = normalTitle
  if (audioContext) audioContext.close()
})
</script>

<template>
  <section class="admin-shell">
    <div v-if="loading" class="admin-login"><p>Opening the LODEX owner dashboard…</p></div>
    <form v-else-if="!authenticated" class="admin-login" @submit.prevent="login">
      <img src="/lodex-logo-home-business.webp" alt="LODEX Home & Business Services" />
      <p class="eyebrow">Owner access</p>
      <h1>Projects, visitors and live support.</h1>
      <p>Use the same administrator token as the Giorgiy Operations Center. It is exchanged for a private, secure session cookie.</p>
      <label>Administrator token<input v-model="token" type="password" autocomplete="current-password" required /></label>
      <button class="primary-button" type="submit">Open dashboard <span>↗</span></button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>

    <template v-else>
      <header class="admin-header">
        <div><p class="eyebrow">LODEX owner dashboard</p><h1>Live work desk</h1><small class="admin-build">v{{ APP_VERSION }} · build {{ shortBuild }}</small></div>
        <div class="admin-header-actions"><button class="outline-button" type="button" @click="enableAlerts">{{ alertsEnabled ? 'Alerts enabled' : 'Enable phone alerts' }}</button><button class="back-button" type="button" @click="logout">Sign out</button></div>
      </header>
      <p v-if="error" class="admin-error">{{ error }}</p>

      <div class="admin-metrics">
        <article><span>On the site now</span><b>{{ overview.active_count || 0 }}</b><small>Anonymous live sessions</small></article>
        <article><span>Visitors today</span><b>{{ overview.visitors_today || 0 }}</b><small>Unique browser sessions</small></article>
        <article><span>Project requests</span><b>{{ overview.counts?.projects || 0 }}</b><small>Latest 100 shown below</small></article>
        <article><span>Waiting for video</span><b>{{ overview.counts?.waiting_support || 0 }}</b><small>Live support requests</small></article>
      </div>

      <section class="admin-panel">
        <div class="admin-panel-heading"><div><p class="eyebrow">Right now</p><h2>Active visitors</h2></div><button class="outline-button" type="button" @click="loadOverview">Refresh</button></div>
        <div v-if="activeVisitors.length" class="admin-visitor-list"><article v-for="visitor in activeVisitors" :key="visitor.visitor_id"><i></i><div><b>{{ visitor.page_title || 'LODEX visitor' }}</b><span>{{ visitor.path }}</span></div><small>{{ formatDate(visitor.last_seen) }}</small></article></div>
        <p v-else class="admin-empty">Nobody is actively browsing right now.</p>
      </section>

      <section ref="supportPanel" :class="['admin-panel', 'support-priority', { 'support-flash': supportFlash }]">
        <div class="admin-panel-heading"><div><p class="eyebrow">Video support</p><h2>Call requests</h2></div><span v-if="supportRequests.some(item => item.status === 'waiting')" class="support-live-badge">LIVE</span></div>
        <div v-if="supportRequests.length" class="admin-support-grid"><article v-for="request in supportRequests" :key="request.id"><span>{{ request.status }}</span><h3>{{ request.name || 'Site visitor' }}</h3><p>{{ request.message || 'Requested a live video visit.' }}</p><small>{{ request.phone || 'No phone provided' }} · {{ formatDate(request.created_at) }}</small><button class="primary-button" type="button" @click="joinRoom(request.room_code)">Join {{ request.room_code }} <b>↗</b></button></article></div>
        <p v-else class="admin-empty">No live support requests yet.</p>
      </section>

      <LeadDesk />

      <section class="admin-panel">
        <div class="admin-panel-heading"><div><p class="eyebrow">Customer inbox</p><h2>Project requests and messages</h2></div></div>
        <div v-if="projectRequests.length" class="admin-project-list">
          <article v-for="request in projectRequests" :key="request.project_code">
            <div class="admin-project-top"><div><span>{{ request.project_code }} · {{ request.status }}</span><h3>{{ request.name }} — {{ request.service_category }}</h3><p>{{ request.address }}</p></div><small>{{ formatDate(request.created_at) }}</small></div>
            <div class="admin-project-meta"><span><b>Division</b>{{ request.customer_segment || 'Legacy record' }}</span><span><b>Assessment</b>{{ request.visit_fee_label || 'Project deposit' }} · {{ formatMoney(request.visit_fee_cents) }}</span><span><b>Requested visit</b>{{ request.preferred_date }} · {{ request.preferred_time }}</span><span><b>Payment</b>{{ request.payment_status }}</span><span><b>Phone</b>{{ request.phone }}</span><span><b>Email</b>{{ request.email || '—' }}</span><span><b>Distance</b>{{ request.distance_miles == null ? 'Pending review' : `${request.distance_miles} miles` }}</span><span><b>Pricing rule</b>{{ request.pricing_rule || 'Legacy server pricing' }}</span></div>
            <p class="admin-summary">{{ request.project_summary }}</p>
            <section v-if="request.uploads?.length" class="admin-attachments" :aria-label="`Customer photos and files for ${request.project_code}`">
              <div class="admin-attachments-heading"><b>Customer photos & files</b><span>{{ request.uploads.length }}</span></div>
              <div class="admin-files">
                <button v-for="file in request.uploads" :key="file.upload_id" type="button" class="admin-file-tile" :aria-label="`Open ${file.filename || 'customer upload'}`" @click="openMedia(file)">
                  <img v-if="isImage(file)" class="admin-file-preview" :src="mediaUrl(file)" :alt="file.description || file.filename || 'Customer upload'" loading="lazy" />
                  <video v-else-if="isVideo(file)" class="admin-file-preview" :src="mediaUrl(file)" muted playsinline preload="metadata"></video>
                  <span v-else class="admin-file-placeholder">FILE</span>
                  <small>{{ file.description || file.filename || (isVideo(file) ? 'Video' : isImage(file) ? 'Photo' : 'Attachment') }}</small>
                </button>
              </div>
            </section>
            <details v-if="request.conversation?.length"><summary>Open complete conversation ({{ request.conversation.length }})</summary><div class="admin-conversation"><p v-for="(message, index) in request.conversation" :key="index" :class="message.role"><b>{{ message.role === 'user' ? request.name : 'LODEX' }}</b>{{ message.text }}</p></div></details>
            <div class="admin-project-actions"><button type="button" class="outline-button" @click="joinRoom(request.project_code)">Join video room</button><select :value="request.status" @change="updateStatus(request, $event.target.value)"><option value="requested">Requested</option><option value="contacted">Contacted</option><option value="scheduled">Scheduled</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></div>
          </article>
        </div>
        <p v-else class="admin-empty">No project requests have been submitted.</p>
      </section>
    </template>

    <div v-if="selectedMedia" class="admin-media-modal" role="dialog" aria-modal="true" :aria-label="selectedMedia.filename || 'Customer upload'" @click.self="closeMedia">
      <button type="button" class="admin-media-close" aria-label="Close full-screen media" @click="closeMedia">×</button>
      <img v-if="isImage(selectedMedia)" :src="mediaUrl(selectedMedia)" :alt="selectedMedia.description || selectedMedia.filename || 'Customer upload'" />
      <video v-else-if="isVideo(selectedMedia)" :src="mediaUrl(selectedMedia)" controls autoplay playsinline></video>
      <div v-else class="admin-media-unsupported">Preview unavailable for this file type.</div>
      <div class="admin-media-caption"><b>{{ selectedMedia.filename || 'Customer upload' }}</b><span>{{ selectedMedia.description || selectedMedia.media_type }}</span></div>
    </div>
  </section>
</template>

<style scoped>
.admin-build { display:block; margin-top:6px; color:#829596; font-size:11px; letter-spacing:.04em; }
.support-priority { scroll-margin-top: 24px; transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.support-live-badge { padding:6px 10px; border-radius:999px; background:#ff554d; color:white; font-size:11px; font-weight:900; letter-spacing:.12em; }
.support-flash { border-color:#ff554d !important; box-shadow:0 0 0 3px rgba(255,85,77,.25), 0 0 40px rgba(255,85,77,.28); animation:support-pulse .8s ease-in-out 5; }
@keyframes support-pulse { 0%,100% { transform:scale(1); } 50% { transform:scale(1.012); } }
.admin-attachments {
  margin: 14px 0;
  padding: 13px;
  border: 1px solid rgba(210, 162, 84, 0.35);
  border-radius: 12px;
  background: #111f21;
}

.admin-attachments-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #edc57b;
  font-size: 11px;
}

.admin-attachments-heading span {
  display: grid;
  place-items: center;
  min-width: 24px;
  height: 24px;
  padding: 0 7px;
  border-radius: 999px;
  background: #d2a254;
  color: #101719;
  font-weight: 900;
}
</style>