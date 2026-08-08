<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { servicePath, services } from './services.js'

const step = ref('chat')
const message = ref('')
const description = ref('')
const selectedFile = ref(null)
const uploaded = ref(null)
const sending = ref(false)
const agreed = ref(false)
const identity = ref({ name: '', location: '' })
const identitySubmitted = ref(false)
const scopeTurns = ref(0)
const contactSubmitted = ref(false)
const contact = ref({ contact: '' })
const contactSending = ref(false)
const contactNotice = ref('')
const listening = ref(false)
const voiceSupported = ref(false)
const voiceStatus = ref('')
const voiceTranscript = ref(false)
const voiceFinal = ref('')
const assessment = ref({
  stage: 'discovery', clarity: 0, project_summary: '', facts: {}, validated_assumptions: [], missing_details: [],
  license_risk: 'possible', license_path: 'review', budget_status: 'unknown', customer_flexibility: 'unknown',
  preliminary_estimate: { status: 'not_ready', note: 'We’ll build a preliminary range once the scope and rate card are ready.' },
})
const scheduleDate = ref('')
const scheduleTime = ref('')
const bookedSlots = ref([])
const availabilityLoading = ref(false)
const availabilityNotice = ref('')
const scheduleSlots = ['11:00', '12:30', '14:00', '15:30', '17:00', '18:30']
const intakeComplete = computed(() => ['ready', 'decline'].includes(assessment.value.stage))
let recognition = null
let voiceRestartTimer = null
let manualVoiceStop = false
const appointment = ref({ name: '', phone: '', email: '', address: '', preferred_date: '', preferred_time: '' })
const notice = ref('')
const support = ref({ name: '', contact: '', message: '' })
const supportSending = ref(false)
const supportNotice = ref('')
const menuOpen = ref(false)
const searchOpen = ref(false)
const searchQuery = ref('')
const currentPath = ref(typeof window !== 'undefined' ? window.location.pathname : '/')
const messages = ref([
  { role: 'assistant', text: 'First, what is your name and where is the project located?', options: [] },
])
const summary = computed(() => messages.value.filter(x => x.role === 'user').map(x => x.text).join('\n').slice(-3000))
const intakeContext = computed(() => assessment.value.project_summary || summary.value.slice(-1200))
const scheduleDates = computed(() => {
  const dates = []
  const today = new Date()
  today.setHours(12, 0, 0, 0)
  for (let offset = 1; dates.length < 10 && offset < 20; offset += 1) {
    const date = new Date(today)
    date.setDate(today.getDate() + offset)
    if (date.getDay() !== 1) dates.push(date)
  }
  return dates
})
const canConfirm = computed(() => messages.value.some(x => x.role === 'assistant' && x.text !== messages.value[0].text) && messages.value.some(x => x.role === 'user'))
const canSchedule = computed(() => agreed.value && contactSubmitted.value && assessment.value.business_fit !== 'decline' && assessment.value.stage === 'ready' && clarity.value >= 100)
const contactReady = computed(() => identitySubmitted.value && scopeTurns.value >= 1 && !contactSubmitted.value)
const clarity = computed(() => Math.max(0, Math.min(100, Number(assessment.value.clarity) || 0)))
const briefFacts = computed(() => [
  ['Work', assessment.value.facts?.scope], ['Where', assessment.value.facts?.site_area], ['Size / quantity', assessment.value.facts?.size_or_quantity],
  ['Timing', assessment.value.facts?.timing], ['Budget', assessment.value.facts?.budget], ['Flexibility', assessment.value.facts?.flexibility],
  ['Permit / licensing', assessment.value.facts?.permit_or_license_path],
].filter(([, value]) => value))
const activeService = computed(() => {
  const path = currentPath.value.replace(/\/+$/, '') || '/'
  return services.find(service => servicePath(service).replace(/\/+$/, '') === path) || null
})
const filteredServices = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return services
  return services.filter(service => `${service.name} ${service.eyebrow} ${service.description}`.toLowerCase().includes(query))
})
const leadServiceSlugs = ['deck-repairs', 'door-repairs', 'garage-shelving', 'store-pickup-installation', 'painting', 'power-washing', 'clean-up-services']
const leadServices = computed(() => leadServiceSlugs.map(slug => services.find(service => service.slug === slug)).filter(Boolean))
function updateSeo() {
  const title = activeService.value ? `${activeService.value.name} in Northeast Ohio | LODEX Home Services` : 'LODEX Home Services | Northeast Ohio'
  const description = activeService.value?.seo || 'A better way to plan, estimate and manage the work that keeps your home moving.'
  document.title = title
  let meta = document.querySelector('meta[name="description"]')
  if (!meta) { meta = document.createElement('meta'); meta.name = 'description'; document.head.appendChild(meta) }
  meta.content = description
  let canonical = document.querySelector('link[rel="canonical"]')
  if (!canonical) { canonical = document.createElement('link'); canonical.rel = 'canonical'; document.head.appendChild(canonical) }
  canonical.href = `${window.location.origin}${activeService.value ? servicePath(activeService.value) : '/'}`
}
function navigate(path) {
  menuOpen.value = false
  searchOpen.value = false
  if (window.location.pathname !== path) window.history.pushState({}, '', path)
  currentPath.value = path
  updateSeo()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function goToIntake() {
  menuOpen.value = false
  if (window.location.pathname !== '/') window.history.pushState({}, '', '/#intake')
  else window.location.hash = 'intake'
  currentPath.value = '/'
  updateSeo()
  nextTick(() => document.querySelector('#intake')?.scrollIntoView({ behavior: 'smooth' }))
}
function openService(service) { navigate(servicePath(service)) }
function toggleMenu() { menuOpen.value = !menuOpen.value; searchOpen.value = false }
function add(role, text, options = []) { messages.value.push({ role, text, options }); nextTick(() => document.querySelector('.messages')?.scrollTo({ top: 99999, behavior: 'smooth' })) }
function dropAssumption(item) {
  const current = assessment.value
  const dismissed = [...new Set([...(current.dismissed_assumptions || []), item])]
  assessment.value = {
    ...current,
    clarity: Math.max(0, (Number(current.clarity) || 0) - 8),
    validated_assumptions: (current.validated_assumptions || []).filter(assumption => assumption !== item),
    missing_details: [...new Set([...(current.missing_details || []), `Replace or confirm: ${item}`])],
    dismissed_assumptions: dismissed,
  }
}
function selectFile(file) {
  if (!file) return
  selectedFile.value = file
}
function onDrop(event) {
  const [file] = [...(event.dataTransfer?.files || [])]
  selectFile(file)
}
function beginIntake() {
  if (!identity.value.name.trim() || !identity.value.location.trim()) return
  identitySubmitted.value = true
  add('user', `${identity.value.name.trim()} — project location: ${identity.value.location.trim()}`)
  add('assistant', 'Now describe what you want done. One or two sentences is enough to start.')
  nextTick(() => document.querySelector('.composer textarea')?.focus())
}
function initVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) return
  voiceSupported.value = true
  recognition = new SpeechRecognition()
  recognition.continuous = true
  recognition.interimResults = true
  recognition.lang = 'en-US'
  recognition.onstart = () => { listening.value = true; voiceStatus.value = 'Listening… pauses are okay. Tap Stop when you are finished.' }
  recognition.onresult = event => {
    let interim = ''
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const part = event.results[i][0].transcript.trim()
      if (event.results[i].isFinal) voiceFinal.value = `${voiceFinal.value} ${part}`.trim()
      else interim += `${part} `
    }
    message.value = `${voiceFinal.value} ${interim}`.trim()
    voiceTranscript.value = true
    voiceStatus.value = 'Still listening… pauses are okay. Tap Stop when you are finished.'
  }
  recognition.onerror = event => {
    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
      manualVoiceStop = true
      listening.value = false
      voiceStatus.value = 'Microphone access was blocked. You can type instead.'
    } else {
      voiceStatus.value = 'Still listening… pauses are okay. Tap Stop when you are finished.'
    }
  }
  recognition.onend = () => {
    if (listening.value && !manualVoiceStop) {
      clearTimeout(voiceRestartTimer)
      voiceRestartTimer = setTimeout(() => { try { recognition.start() } catch {} }, 250)
      return
    }
    listening.value = false
    if (voiceFinal.value) voiceStatus.value = 'Transcript ready — review it, then send to confirm what we heard.'
  }
}
function toggleVoice() {
  if (!identitySubmitted.value) return
  if (!voiceSupported.value) { voiceStatus.value = 'Voice transcription is not supported in this browser. Try Chrome or Safari over HTTPS.'; return }
  if (listening.value) { manualVoiceStop = true; recognition.stop(); return }
  manualVoiceStop = false
  voiceFinal.value = message.value.trim()
  voiceStatus.value = 'Starting microphone…'
  try { recognition.start() } catch { voiceStatus.value = 'Microphone is already starting. Try again in a moment.' }
}
async function upload() {
  if (!selectedFile.value) return
  const form = new FormData(); form.append('file', selectedFile.value); form.append('description', description.value)
  sending.value = true
  try {
    const r = await fetch('/api/intake/upload', { method: 'POST', body: form }); const data = await readResponse(r)
    if (!r.ok) throw new Error(data.detail || 'Upload failed')
    uploaded.value = data; add('assistant', `I received ${data.filename}.\n\n${data.analysis}`)
  } catch (e) { add('assistant', e.message) } finally { sending.value = false }
}
async function send() {
  const text = message.value.trim(); if (!text || sending.value || !identitySubmitted.value || intakeComplete.value) return
  const wasVoiceTranscript = voiceTranscript.value
  message.value = ''; voiceTranscript.value = false; voiceStatus.value = ''; add('user', text); sending.value = true
  try {
    const r = await fetch('/api/intake/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, project_summary: intakeContext.value, media_notes: uploaded.value ? `${uploaded.value.filename}: ${description.value}` : '', voice_transcript: wasVoiceTranscript, customer_name: identity.value.name.trim(), project_location: identity.value.location.trim(), intake_stage: assessment.value.stage || 'scope', intake_turns: scopeTurns.value, assessment: assessment.value }) })
    const data = await readResponse(r); if (!r.ok) throw new Error(data.detail || 'Unable to analyze right now')
    assessment.value = data.assessment || {}
    scopeTurns.value += 1
    add('assistant', data.reply, data.options || [])
  } catch (e) { add('assistant', `${e.message} You can also leave a message in the support box and we’ll follow up.`) } finally { sending.value = false }
}
function sendOption(option) {
  message.value = option
  voiceTranscript.value = false
  send()
}
async function submitContact() {
  if (!contact.value.contact.trim() || contactSending.value) return
  contactSending.value = true; contactNotice.value = ''
  try {
    const r = await fetch('/api/support/message', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: identity.value.name.trim(), contact: contact.value.contact.trim(), message: `Project location: ${identity.value.location.trim()}\nProject details: ${summary.value}` }) })
    const data = await readResponse(r)
    if (!r.ok) throw new Error(data.detail || 'Could not save your contact information')
    contactSubmitted.value = true
    contactNotice.value = data.message
    add('assistant', 'Got it. We’ll review the details and get back to you by email or phone. If you want, you can keep adding project details here.')
  } catch (e) { contactNotice.value = e.message } finally { contactSending.value = false }
}
async function readResponse(response) {
  const text = await response.text()
  try { return text ? JSON.parse(text) : {} } catch { return { detail: text || 'The server returned an unreadable response.' } }
}
function readyToSchedule() {
  if (!canSchedule.value) return
  appointment.value.name = identity.value.name.trim()
  if (contact.value.contact.includes('@')) appointment.value.email = contact.value.contact.trim()
  else if (contact.value.contact) appointment.value.phone = contact.value.contact.trim()
  step.value = 'schedule'
  add('assistant', 'Great. Select a preferred day and time for a meet-and-greet. The appointment is requested—not final—until we confirm the visit and final scope.')
}
function isoDate(date) { return date.toISOString().slice(0, 10) }
function dayName(date) { return date.toLocaleDateString('en-US', { weekday: 'short' }) }
function monthName(date) { return date.toLocaleDateString('en-US', { month: 'short' }) }
function prettyTime(value) {
  const [hour, minute] = value.split(':').map(Number)
  const suffix = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour > 12 ? hour - 12 : hour
  return `${displayHour}:${String(minute).padStart(2, '0')} ${suffix}`
}
async function loadAvailability() {
  if (!scheduleDate.value) return
  availabilityLoading.value = true
  availabilityNotice.value = ''
  scheduleTime.value = ''
  try {
    const r = await fetch(`/api/appointments/availability?date=${encodeURIComponent(scheduleDate.value)}`)
    const data = await readResponse(r)
    if (!r.ok) throw new Error(data.detail || 'Could not load visit times')
    bookedSlots.value = data.booked || []
    if (data.closed) availabilityNotice.value = 'We do not schedule visits on Mondays.'
  } catch (e) {
    bookedSlots.value = []
    availabilityNotice.value = e.message
  } finally { availabilityLoading.value = false }
}
function chooseScheduleDate(date) { scheduleDate.value = isoDate(date) }
async function book() {
  if (!scheduleDate.value || !scheduleTime.value) { notice.value = 'Choose a day and available time before requesting the visit.'; return }
  sending.value = true; notice.value = ''
  try {
    const uploads = uploaded.value ? [{ upload_id: uploaded.value.upload_id, filename: uploaded.value.filename, media_type: uploaded.value.media_type, description: description.value }] : []
    const r = await fetch('/api/appointments/request', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...appointment.value, preferred_date: scheduleDate.value, preferred_time: scheduleTime.value, project_summary: summary.value, uploads, assumptions_confirmed: agreed.value, intake_assessment: assessment.value }) }); const data = await readResponse(r)
    if (!r.ok) throw new Error(data.detail || 'Could not request appointment')
    notice.value = data.message; step.value = 'done'
  } catch (e) { notice.value = e.message } finally { sending.value = false }
}
async function sendSupport() {
  if (supportSending.value) return
  supportSending.value = true; supportNotice.value = ''
  try {
    const r = await fetch('/api/support/message', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(support.value) })
    const data = await readResponse(r)
    if (!r.ok) throw new Error(data.detail || 'Could not send your message')
    supportNotice.value = data.message
    support.value = { name: '', contact: '', message: '' }
  } catch (e) { supportNotice.value = e.message } finally { supportSending.value = false }
}
if (typeof window !== 'undefined') initVoice()
onMounted(() => {
  updateSeo()
  window.addEventListener('popstate', () => { currentPath.value = window.location.pathname; updateSeo(); menuOpen.value = false })
})
watch(step, value => {
  if (value === 'schedule' && !scheduleDate.value) scheduleDate.value = isoDate(scheduleDates.value[0])
})
watch(scheduleDate, loadAvailability)
onBeforeUnmount(() => { manualVoiceStop = true; clearTimeout(voiceRestartTimer); if (recognition && listening.value) recognition.stop() })
</script>

<template>
  <main v-if="activeService" class="service-page">
    <nav class="site-header"><button class="menu-toggle" type="button" aria-label="Open services menu" @click="toggleMenu">☰</button><a class="brand" href="/" @click.prevent="navigate('/')"><span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span><span><b>LO</b>DEX<small>HOME SERVICES · NORTHEAST OHIO</small></span></a><div class="top-tools"><button class="search-toggle" type="button" @click="searchOpen = !searchOpen">⌕ <span>Search</span></button><a class="header-cta" href="#intake" @click.prevent="goToIntake">Plan my project <span>↗</span></a></div></nav>
    <div class="drawer-backdrop" v-if="menuOpen" @click="menuOpen = false"></div><aside class="service-drawer" :class="{ open: menuOpen }"><div class="drawer-head"><b>LODEX SERVICES</b><button type="button" aria-label="Close services menu" @click="menuOpen = false">×</button></div><input v-model="searchQuery" placeholder="Search services" aria-label="Search services"/><a v-for="service in filteredServices" :key="service.slug" href="#" @click.prevent="openService(service)">{{ service.name }} <span>↗</span></a></aside>
    <div v-if="searchOpen" class="search-panel"><input v-model="searchQuery" autofocus placeholder="Search services" aria-label="Search services"/><a v-for="service in filteredServices.slice(0, 6)" :key="service.slug" href="#" @click.prevent="openService(service)">{{ service.name }}</a></div>
    <section class="service-hero"><div><p class="eyebrow">{{ activeService.eyebrow }} · Northeast Ohio</p><h1>{{ activeService.name }}<br/><em>done clearly.</em></h1><p class="service-lede">{{ activeService.description }}</p><a class="cta" href="#intake" @click.prevent="goToIntake">Tell us about this work <span>→</span></a></div><div class="service-visual"><span>LODEX / SERVICE REVIEW</span><strong>{{ activeService.name }}</strong><small>Scope first · price and scheduling next</small></div></section>
    <section class="service-details"><div><p class="eyebrow">What we’ll clarify</p><h2>Start with the actual condition.</h2></div><div><p>Every job starts with a short description, the location, and the details that affect scope. If the work needs a licensed trade or permit, we flag that before promising a visit.</p><ul><li v-for="detail in activeService.details" :key="detail">{{ detail }} <span>↗</span></li></ul></div></section>
    <section id="intake" class="service-cta"><p class="eyebrow">Ready when you are</p><h2>Describe the work in your own words.</h2><p>LODEX asks only for the details needed to finish the project brief, check the licensing path, compare a preliminary benchmark with your budget, and book the right next step.</p><a class="cta" href="/" @click.prevent="goToIntake">Open the project chat <span>→</span></a></section>
    <footer>LODEX Construction Maintenance and Repair <span>•</span> Northeast Ohio</footer>
  </main>
  <main v-else>
    <nav class="site-header"><button class="menu-toggle" type="button" aria-label="Open services menu" @click="toggleMenu">☰</button><a class="brand" href="#top"><span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span><span><b>LO</b>DEX<small>HOME SERVICES · NORTHEAST OHIO</small></span></a><div class="nav-links"><a href="#services">Services</a><a href="#intake">How it works</a><a href="#intake">Request a visit</a></div><div class="top-tools"><button class="search-toggle" type="button" @click="searchOpen = !searchOpen">⌕ <span>Search</span></button><a class="header-cta" href="#intake" @click.prevent="goToIntake">Plan my project <span>↗</span></a></div></nav>
    <div class="drawer-backdrop" v-if="menuOpen" @click="menuOpen = false"></div><aside class="service-drawer" :class="{ open: menuOpen }"><div class="drawer-head"><b>LODEX SERVICES</b><button type="button" aria-label="Close services menu" @click="menuOpen = false">×</button></div><input v-model="searchQuery" placeholder="Search services" aria-label="Search services"/><a v-for="service in filteredServices" :key="service.slug" href="#" @click.prevent="openService(service)">{{ service.name }} <span>↗</span></a></aside>
    <div v-if="searchOpen" class="search-panel"><input v-model="searchQuery" autofocus placeholder="Search services" aria-label="Search services"/><a v-for="service in filteredServices.slice(0, 6)" :key="service.slug" href="#" @click.prevent="openService(service)">{{ service.name }}</a></div>
    <section class="hero hero-intake" id="top"><div class="hero-copy"><p class="eyebrow"><span class="status-dot"></span>Northeast Ohio home projects</p><h1>Whatcha tryna<br/><em>do?</em><span class="terminal-cursor" aria-hidden="true">|</span></h1><p class="lede">Type it, say it, or drop in a photo or video. We qualify the scope, site conditions, licensing path, timing, and budget—then show the right next step.</p><div class="hero-proof"><span><b>01</b>Describe the project</span><span><b>02</b>Qualify the job</span><span><b>03</b>See the next step</span></div></div></section>
    <section id="intake" class="intake"><div class="flow"><span :class="{active:step==='chat'}">1. Understand</span><span :class="{active:step==='schedule'}">2. Meet</span><span :class="{active:step==='done'}">3. Confirm</span></div>
      <div v-if="step === 'chat'" class="workspace"><div class="chat" @dragover.prevent @drop.prevent="onDrop"><div class="chat-title"><i></i><div><b>Project qualification</b><small>We ask only what changes the scope, price, licensing path, or next step.</small></div><span class="turn-count">{{ clarity }}% ready</span></div><div class="identity-gate" v-if="!identitySubmitted"><p>Start with your name and project location. Then describe the job in your own words.</p><form @submit.prevent="beginIntake"><input v-model="identity.name" required placeholder="Your name"/><input v-model="identity.location" required placeholder="Project city or ZIP"/><button class="send-button" type="submit">Start chat</button></form></div><div class="messages"><article v-for="(item,i) in messages" :key="i" :class="item.role"><p>{{ item.text }}</p><div v-if="item.role === 'assistant' && item.options?.length && !intakeComplete" class="quick-replies"><button v-for="option in item.options" :key="option" type="button" @click="sendOption(option)" :disabled="sending">{{ option }}</button></div></article><div v-if="sending" class="assistant"><p class="typing">Updating the project brief…</p></div><div v-if="contactReady" class="contact-prompt"><b>Where should we follow up?</b><p>You can keep chatting, or leave an email/mobile now so the next step is ready when the project is clear.</p><form @submit.prevent="submitContact"><input v-model="contact.contact" required placeholder="Email or mobile number"/><button class="send-button" :disabled="contactSending">{{ contactSending ? 'Saving…' : 'Save contact' }}</button></form><p v-if="contactNotice" class="notice">{{ contactNotice }}</p></div><div v-if="intakeComplete" class="intake-complete"><b>Brief ready.</b><span>We have what we need to check licensing, budget fit, and the best way to meet. Add your contact details above and we’ll line up the next step.</span></div></div><form @submit.prevent="send" class="composer"><div class="composer-input"><textarea v-model="message" :disabled="sending || listening || !identitySubmitted || intakeComplete" @input="voiceTranscript = false" placeholder="Describe the work, ask a question, or add a detail…" rows="3"></textarea><label class="chat-file" title="Attach a photo or video"><input type="file" accept="image/jpeg,image/png,image/webp,image/heic,video/mp4,video/quicktime,video/webm" @change="selectFile($event.target.files[0])"/>＋</label><button type="button" class="voice-button" :class="{ listening }" :disabled="intakeComplete" :aria-label="listening ? 'Stop recording' : 'Record a voice message'" :title="listening ? 'Stop recording' : 'Record a voice message'" @click="toggleVoice"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"></rect><path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8"></path></svg><span>{{ listening ? 'Stop' : 'Voice' }}</span></button></div><button class="send-button" :disabled="sending || listening || !identitySubmitted || intakeComplete || !message.trim()">Send</button></form><div class="drop-strip" :class="{ attached: selectedFile }"><span>{{ selectedFile ? `Attached: ${selectedFile.name}` : 'Drop a photo or video anywhere in this chat, or use ＋.' }}</span><button v-if="selectedFile" type="button" class="attach-button" @click="upload" :disabled="sending">{{ sending ? 'Analyzing…' : 'Analyze attachment' }}</button></div><p v-if="voiceStatus" class="voice-status" role="status">{{ voiceStatus }}</p><p v-else-if="!voiceSupported" class="voice-status muted">Voice transcription works best in Chrome or Safari over HTTPS.</p></div>
        <aside class="project-brief"><div class="brief-head"><div><p class="eyebrow">Lead qualification</p><h2>{{ clarity }}% ready</h2></div><div class="clarity-dial" :style="{ '--clarity': `${clarity}%` }"><span>{{ clarity }}%</span></div></div><div class="clarity-track"><i :style="{ width: `${clarity}%` }"></i></div><p class="brief-summary">{{ assessment.project_summary || 'As you explain the project, confirmed details and working assumptions appear here.' }}</p><dl class="brief-facts"><template v-for="([label, value]) in briefFacts" :key="label"><dt>{{ label }}</dt><dd>{{ value }}</dd></template></dl><div class="brief-list" v-if="assessment.validated_assumptions?.length"><b>Confirmed</b><span v-for="item in assessment.validated_assumptions" :key="item">✓ {{ item }} <button type="button" title="Remove this assumption" @click="dropAssumption(item)">×</button></span></div><div class="brief-list missing" v-if="assessment.missing_details?.length"><b>Still useful</b><span v-for="item in assessment.missing_details" :key="item">• {{ item }}</span></div><div class="decision-card"><b>Licensing & delivery</b><span>{{ assessment.license_path === 'gc_subcontractor_review' ? 'General-contractor / subcontractor review' : assessment.license_path === 'licensed_referral' ? 'Licensed trade referral review' : 'Scope review in progress' }}</span></div><div class="decision-card"><b>Preliminary range</b><span>{{ assessment.preliminary_estimate?.range || assessment.preliminary_estimate?.note }}</span></div><label class="confirm"><input v-model="agreed" type="checkbox" :disabled="!canConfirm"/> The working assumptions above look right to me.</label><p v-if="assessment.business_fit === 'decline'" class="assessment-note">This looks like work that may need a licensed trade referral before any visit is scheduled.</p><button class="ready" @click="readyToSchedule" :disabled="!canSchedule">Book meet-and-greet →</button><div class="brief-support"><b>Need help now?</b><form class="support-form" @submit.prevent="sendSupport"><input v-model="support.name" required placeholder="Your name"/><input v-model="support.contact" required placeholder="Email or mobile"/><textarea v-model="support.message" required placeholder="Short message" rows="2"></textarea><button class="outline" :disabled="supportSending">{{ supportSending ? 'Sending…' : 'Request help' }}</button></form><p v-if="supportNotice" class="notice">{{ supportNotice }}</p></div></aside></div>
      <form v-else-if="step === 'schedule'" @submit.prevent="book" class="schedule"><div class="schedule-heading"><div><p class="eyebrow">Next: a real-world check</p><h2>Claim a visit window.</h2><p>Pick a preferred slot. We’ll review the details and confirm by phone or email before the visit is final.</p></div><span class="schedule-note">Eastern time<br/>Tuesday–Sunday</span></div><fieldset><legend><b>01</b> PICK A DAY</legend><div class="date-row"><button v-for="date in scheduleDates" :key="isoDate(date)" type="button" class="date" :class="{ active: scheduleDate === isoDate(date) }" @click="chooseScheduleDate(date)"><small>{{ dayName(date) }}</small><strong>{{ date.getDate() }}</strong><small>{{ monthName(date) }}</small></button></div></fieldset><fieldset><legend><b>02</b> PICK A TIME <span>Eastern time</span></legend><div v-if="availabilityLoading" class="availability-loading">Checking available visit windows…</div><div v-else class="time-grid"><button v-for="slot in scheduleSlots" :key="slot" type="button" class="time" :class="{ active: scheduleTime === slot }" :disabled="bookedSlots.includes(slot)" @click="scheduleTime = slot">{{ bookedSlots.includes(slot) ? 'REQUESTED' : prettyTime(slot) }}</button></div><p v-if="availabilityNotice" class="availability-notice">{{ availabilityNotice }}</p></fieldset><fieldset><legend><b>03</b> CONFIRM YOUR DETAILS</legend><div class="fields"><label>Your name<input v-model="appointment.name" required placeholder="Your name" autocomplete="name"/></label><label>Phone<input v-model="appointment.phone" required placeholder="(216) 555-0123" autocomplete="tel"/></label><label>Email <span>(optional)</span><input v-model="appointment.email" type="email" placeholder="you@example.com" autocomplete="email"/></label><label>Job address<input v-model="appointment.address" required placeholder="Where should we meet?" autocomplete="street-address"/></label></div></fieldset><p v-if="notice" class="notice">{{ notice }}</p><button class="submit cta" :disabled="sending || availabilityLoading">{{ sending ? 'Sending request…' : 'Request meet-and-greet' }} <span>→</span></button><p class="privacy">Your preferred time is a request, not a final booking. We use your details only to arrange the visit.</p></form>
      <div v-else class="schedule done"><p class="eyebrow">Request received</p><h2>We’ll confirm the visit shortly.</h2><p>{{ notice }}</p></div>
    </section>
    <section class="services lead-services"><p class="eyebrow">Start here</p><h2>The work LODEX leads with.</h2><p class="section-lede">Deck and door repairs, garage storage, pickup and installation, touch-ups and turnover fixes, plus exterior cleanup.</p><div class="service-grid"><a v-for="service in leadServices" :key="service.slug" class="service-card-link" :href="servicePath(service)" @click.prevent="openService(service)"><b>{{ service.name }}</b><span>{{ service.description }}</span><i>Explore service ↗</i></a></div></section>
    <section class="inspiration"><img src="/inspiration/what-is-possible.png" alt="Concept examples of built-ins, refreshed interiors, a TV upgrade, and a custom wood entry"/><div><p class="eyebrow">What’s possible</p><h2>Bring the idea. We’ll help turn it into a plan.</h2><p>Concept inspiration—not a claim of past customer work. Upload the space you actually have, and the intake will narrow the next practical step.</p><a class="text-link" href="#intake" @click.prevent="goToIntake">Explore a custom idea →</a></div></section>
    <section class="services" id="services"><p class="eyebrow">Small jobs welcome</p><h2>Clear work categories. Clear scope.</h2><div class="service-grid"><a v-for="service in services" :key="service.slug" class="service-card-link" :href="servicePath(service)" @click.prevent="openService(service)"><b>{{ service.name }}</b><span>{{ service.description }}</span><i>Explore service ↗</i></a></div><p class="area"><b>Serving Cleveland’s east side and surrounding communities.</b> Tell us the job address early so we can confirm that the visit fits the service area.</p></section>
    <section class="proof"><p class="eyebrow">How we earn the proof</p><h2>No made-up reviews. Every completed project becomes a documented before/after story—with customer permission.</h2><p>That gives new customers real work to judge, and it gives LODEX an honest portfolio and review base as projects are completed.</p></section>
    <footer>LODEX Construction Maintenance and Repair <span>•</span> Northeast Ohio <span>•</span> Final price is confirmed after scope validation.</footer>
  </main>
</template>

<style scoped>
.intent-row { display:flex; justify-content:center; flex-wrap:wrap; gap:10px; margin:28px auto 15px; }
.intent { min-width:112px; background:#fff; color:#141b22; border:1px solid #141b22; border-radius:999px; transition:transform .18s ease, background .18s ease, color .18s ease; }
.intent:hover,.intent:focus-visible { background:#141b22; color:#fff; transform:translateY(-2px); }
.microcopy { color:#716b63; font-size:14px; margin:0; }
.quick-replies { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.quick-replies button { padding:9px 11px; border:1px solid #c9c1b8; background:#fff; color:var(--ink); border-radius:999px; font-size:12px; }
.quick-replies button:hover,.quick-replies button:focus-visible { background:#262f36; color:#fff; border-color:#262f36; }
.identity-gate { padding:18px 24px; border-bottom:1px solid #eee; background:#fbfaf8; }
.identity-gate p { margin:0 0 10px; font-weight:700; font-size:13px; }
.identity-gate form { display:grid; grid-template-columns:1fr 1fr auto; gap:9px; align-items:center; }
.identity-gate form input { min-width:0; }
.contact-prompt { margin:22px 0 6px; padding:16px; border:1px solid #ead7c9; background:#fff8f3; border-radius:5px; }
.contact-prompt b { display:block; margin-bottom:4px; }
.contact-prompt p { padding:0!important; margin:0 0 10px!important; background:transparent!important; color:#5e5952; font-size:13px; }
.contact-prompt form { display:flex; gap:8px; }
.contact-prompt form input { min-width:0; }
.intake-complete { display:flex; flex-direction:column; gap:4px; margin:12px 0 6px; padding:14px 16px; border-left:3px solid var(--coral); background:#e8e7dd; color:#12312e; font-size:13px; }
.intake-complete span { color:#5e6f68; line-height:1.45; }
.terminal-cursor { display:inline-block; margin-left:8px; color:var(--orange); font-family:'DM Mono'; font-weight:400; animation:terminal-blink 1s steps(1,end) infinite; }
.inspiration { display:grid; grid-template-columns:1.25fr .75fr; align-items:stretch; margin:0 auto; max-width:1200px; background:#ded3c6; }
.inspiration img { width:100%; min-height:320px; height:100%; object-fit:cover; display:block; }
.inspiration > div { padding:52px 42px; align-self:center; }
.inspiration h2 { font-size:clamp(28px,4vw,48px); letter-spacing:-.06em; line-height:1.04; margin:12px 0; }
.inspiration p:not(.eyebrow) { line-height:1.65; color:#514d47; }
.text-link { padding:0; color:#141b22; background:transparent; border-bottom:1px solid #141b22; border-radius:0; margin-top:12px; }
.service-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin:28px 0; }
.service-grid article { padding:20px; border:1px solid #d8d3ca; background:#fff; border-radius:5px; }
.service-grid b { display:block; margin-bottom:7px; font-size:16px; }
.service-grid span,.area { color:#5e5952; line-height:1.55; }
.proof { background:#efe6db; padding:76px max(24px,calc((100vw - 900px)/2)); text-align:center; }
.proof h2 { font-size:clamp(26px,4vw,47px); letter-spacing:-.05em; line-height:1.1; margin:12px auto; }
.proof p:last-child { max-width:680px; margin:0 auto; color:#5e5952; line-height:1.65; }
.support-form { display:flex; flex-direction:column; gap:9px; }
.support-form textarea { min-height:78px; margin:0; }
.support-form .outline { margin:0; }
.divider { display:flex; align-items:center; gap:10px; margin:20px 0 4px; color:#8a8279; font:10px 'DM Mono'; text-transform:uppercase; letter-spacing:.08em; }
.divider:before,.divider:after { content:''; height:1px; flex:1; background:#e2ddd5; }
.assessment-note { color:#8d3d26; font-size:12px; line-height:1.45; }
.composer-input { flex:1; position:relative; display:flex; align-items:stretch; }
.composer-input textarea { flex:1; padding-right:84px; resize:vertical; min-height:76px; }
.voice-button { position:absolute; right:8px; bottom:8px; width:64px; padding:8px 6px; display:flex; flex-direction:column; align-items:center; gap:2px; background:#f0ede8; color:var(--ink); border:1px solid #d7d2c9; font-size:10px; }
.voice-button svg { width:23px; height:23px; fill:none; stroke:currentColor; stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round; }
.voice-button:hover,.voice-button:focus-visible,.voice-button.listening { background:var(--orange); color:#fff; border-color:var(--orange); }
.voice-button.listening svg { animation:voice-pulse 1s ease-in-out infinite; }
.send-button { align-self:stretch; min-width:76px; }
.voice-status { margin:0; padding:0 16px 15px; color:#8d3d26; font:11px 'DM Mono'; line-height:1.5; }
.voice-status.muted { color:#777; }
.hero-intake { min-height:0; display:block; margin:0 auto; padding:52px 0 12px; }
.hero-intake { width:100%; position:relative; overflow:hidden; padding:74px max(24px,calc((100vw - 1120px)/2)) 42px; background:var(--deep); color:var(--paper); }
.hero-intake:before { content:''; position:absolute; inset:0; background:linear-gradient(#d3ff5612 1px,transparent 1px),linear-gradient(90deg,#d3ff5612 1px,transparent 1px); background-size:64px 64px; mask-image:linear-gradient(90deg,black,transparent 75%); }
.hero-intake:after { content:''; position:absolute; left:-10%; right:-10%; top:58%; height:1px; background:var(--lime); box-shadow:0 0 14px var(--lime),0 0 44px var(--lime); transform:rotate(-12deg); opacity:.55; }
.hero-intake .hero-copy { position:relative; z-index:1; max-width:900px; }
.hero-intake .eyebrow { color:#a9beb7; }.status-dot { display:inline-block; width:7px; height:7px; margin-right:8px; border-radius:50%; background:var(--lime); box-shadow:0 0 0 4px #d3ff561c; }
.hero-intake h1 { font-family:Inter,Arial,sans-serif; font-weight:900; letter-spacing:-.085em; line-height:.84; }.hero-intake h1 em { color:var(--lime); font-family:var(--serif); font-weight:400; letter-spacing:-.07em; }
.hero-intake .lede { max-width:690px; margin-bottom:22px; color:#c0cdc6; font-size:17px; }.hero-intake .hero-proof { margin-top:30px; color:#9fb0a8; text-transform:uppercase; letter-spacing:.08em; font-size:10px; }.hero-intake .hero-proof b { color:var(--lime); }
.intake { padding-top:28px; }
.workspace { grid-template-columns:minmax(0,1.65fr) minmax(320px,.72fr); align-items:start; }
.chat { min-height:0; height:min(690px,calc(100vh - 190px)); }
.chat-title { align-items:flex-start; }
.turn-count { margin-left:auto; color:#5e6f68; font:10px/1.4 'DM Mono'; text-align:right; }
.messages { min-height:0; }
.composer { position:relative; }
.chat-file { position:absolute; z-index:2; right:80px; bottom:8px; display:grid; width:34px; height:34px; place-items:center; border:1px solid #aebbb3; background:#fff; color:var(--ink); cursor:pointer; font-size:20px; }
.chat-file input { display:none; }
.composer-input textarea { padding-right:124px; }
.drop-strip { display:flex; align-items:center; justify-content:space-between; gap:12px; min-height:42px; padding:9px 16px; border-top:1px dashed #b8c3bb; background:#edf0e9; color:#5e6f68; font-size:11px; }
.drop-strip.attached { background:#e4f4cb; color:#244330; }
.attach-button { flex:none; padding:7px 10px; border:0; background:var(--ink); color:#fff; font-size:10px; font-weight:800; }
.project-brief { position:sticky; top:18px; padding:24px; background:#e8e7dd; color:var(--ink); max-height:calc(100vh - 36px); overflow:auto; }
.brief-head { display:flex; justify-content:space-between; align-items:flex-start; gap:15px; }
.brief-head .eyebrow { margin-bottom:7px; }
.brief-head h2 { margin:0; font-family:var(--serif); font-size:32px; font-weight:400; letter-spacing:-1px; }
.clarity-dial { --clarity:0%; position:relative; display:grid; width:58px; aspect-ratio:1; place-items:center; border-radius:50%; background:conic-gradient(var(--coral) var(--clarity),#cfd6ce 0); }
.clarity-dial:before { content:''; position:absolute; width:45px; aspect-ratio:1; border-radius:50%; background:#e8e7dd; }
.clarity-dial span { position:relative; font:10px 'DM Mono'; }
.clarity-track { height:6px; margin:18px 0; background:#ccd5cb; }
.clarity-track i { display:block; height:100%; background:var(--coral); transition:width .25s ease; }
.brief-summary { margin:0 0 18px; color:#52655e; font-size:13px; line-height:1.55; }
.brief-facts { display:grid; grid-template-columns:90px 1fr; margin:0 0 18px; font-size:12px; }
.brief-facts dt,.brief-facts dd { margin:0; padding:7px 0; border-top:1px solid #c8d0c8; }
.brief-facts dt { color:#60746a; font:10px 'DM Mono'; text-transform:uppercase; }
.brief-facts dd { font-weight:700; }
.brief-list { display:flex; flex-direction:column; gap:6px; margin:16px 0; font-size:11px; }
.brief-list b { color:#60746a; font:10px 'DM Mono'; text-transform:uppercase; }
.brief-list span { display:flex; justify-content:space-between; gap:8px; padding:7px 8px; background:#f6f7f2; }
.brief-list span button { margin:-3px -3px -3px auto; border:0; background:transparent; color:#8d3d26; font-size:17px; line-height:1; }
.brief-list.missing span { background:#f5eadf; }
.decision-card { display:flex; flex-direction:column; gap:4px; margin:12px 0; padding:12px; border-left:3px solid var(--coral); background:#f6f7f2; font-size:12px; }
.decision-card b { font-size:11px; }
.decision-card span { color:#52655e; line-height:1.4; }
.project-brief .confirm { margin:18px 0 12px; color:#52655e; font-size:11px; line-height:1.5; }
.project-brief .ready { width:100%; }
.brief-support { margin-top:22px; padding-top:18px; border-top:1px solid #c8d0c8; }
.brief-support>b { display:block; margin-bottom:10px; font-size:12px; }
.brief-support .support-form { gap:7px; }
.brief-support .support-form input,.brief-support .support-form textarea { background:#f9faf6; }
@keyframes terminal-blink { 0%,48% { opacity:1; } 49%,100% { opacity:0; } }
@keyframes voice-pulse { 50% { transform:scale(1.12); } }
@media(max-width:900px){ .workspace { grid-template-columns:1fr; }.chat { height:auto; min-height:590px; max-height:none; }.project-brief { position:static; max-height:none; }.hero-intake { padding-top:38px; } }
@media(max-width:760px){ .inspiration { grid-template-columns:1fr; margin:0; }.inspiration img { min-height:220px; }.inspiration > div { padding:36px 24px; }.identity-gate form { grid-template-columns:1fr; }.contact-prompt form { flex-direction:column; }.hero-intake .hero-proof { font-size:10px; }.turn-count { display:none; }.drop-strip { align-items:flex-start; flex-direction:column; }.chat-file { right:78px; } }
@media(max-width:640px){ .service-grid { grid-template-columns:1fr; }.intent { min-width:calc(50% - 8px); } }
</style>
