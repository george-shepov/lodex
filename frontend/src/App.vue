<script setup>
import { computed, nextTick, ref } from 'vue'

const phone = '216-268-2990'
const step = ref('chat')
const message = ref('')
const description = ref('')
const selectedFile = ref(null)
const uploaded = ref(null)
const sending = ref(false)
const agreed = ref(false)
const supportOpen = ref(false)
const galleryOpen = ref(null)
const projectCode = ref('')
const projectPhone = ref('')
const project = ref(null)
const projectError = ref('')
const appointment = ref({ name: '', phone: '', email: '', address: '', preferred_date: '', preferred_time: '' })
const notice = ref('')
const messages = ref([
  { role: 'assistant', text: 'What are you trying to build, fix, upgrade, or customize? Tell us in your own words—or show us the space.' },
])

const galleryItems = [
  { title: 'Warm kitchen, custom feel', category: 'Customize', image: 'https://lzcustom.com/assets/gallery/projects/kitchen-granite-hd.png' },
  { title: 'Handcrafted cabinet details', category: 'Build', image: 'https://lzcustom.com/assets/gallery/projects/custom-cabinets-hd.png' },
  { title: 'Stone that becomes the room', category: 'Upgrade', image: 'https://lzcustom.com/assets/gallery/projects/bathroom-marble-hd.png' },
  { title: 'Precision tile patterns', category: 'Upgrade', image: 'https://lzcustom.com/assets/gallery/u6358423361_Intricate_geometric_tile_pattern_flooring_expert__bec8e5ac-8a9c-4831-8c48-d865023de519_0.png' },
  { title: 'A workshop built for detail', category: 'Build', image: 'https://lzcustom.com/assets/gallery/u6358423361_Professional_stone_fabrication_workshop_with_gran_b43cb579-df0b-4d0e-afa0-00fc79398a29_0.png' },
  { title: 'Materials worth looking at twice', category: 'Customize', image: 'https://lzcustom.com/assets/gallery/projects/granite-samples.jpg' },
  { title: 'A cleaner, finished space', category: 'Fix', image: 'https://lzcustom.com/assets/gallery/u6358423361_Professional_commercial_interior_painting_premium_fe294b7e-0227-404b-bed4-28fc32e6bb35_0.png' },
  { title: 'Built around the way you live', category: 'Build', image: 'https://lzcustom.com/assets/gallery/u6358423361_Luxury_kitchen_interior_with_handcrafted_oak_cabi_6ac455ef-ff90-49ca-baf3-971aab706a90_0.png' },
]

const intents = ['Build', 'Fix', 'Upgrade', 'Customize']
const summary = computed(() => messages.value.filter(item => item.role === 'user').map(item => item.text).join('\n'))
const hasCustomerMessage = computed(() => messages.value.some(item => item.role === 'user'))
const scopePercent = computed(() => agreed.value ? 100 : Math.min(88, messages.value.filter(item => item.role === 'user').length * 22))
const scopeLabel = computed(() => agreed.value ? 'Scope confirmed' : hasCustomerMessage.value ? 'Scope in conversation' : 'Ready when you are')
const canSchedule = computed(() => hasCustomerMessage.value || uploaded.value)

function add(role, text) {
  messages.value.push({ role, text })
  nextTick(() => document.querySelector('.messages')?.scrollTo({ top: 99999, behavior: 'smooth' }))
}

function chooseIntent(intent) {
  const starters = {
    Build: 'I want to build something for my home.',
    Fix: 'I need to fix something at my home.',
    Upgrade: 'I want to upgrade part of my home.',
    Customize: 'I want to customize something in my home.',
  }
  message.value = starters[intent]
  document.querySelector('#intake')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  nextTick(() => document.querySelector('.composer textarea')?.focus())
}

function openSchedule() {
  step.value = 'schedule'
  document.querySelector('#intake')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function openSupport() {
  supportOpen.value = !supportOpen.value
  if (supportOpen.value) nextTick(() => document.querySelector('.support-input')?.focus())
}

function imageFallback(event) {
  event.target.classList.add('image-failed')
  event.target.removeAttribute('src')
}

async function upload() {
  if (!selectedFile.value) return
  const form = new FormData()
  form.append('file', selectedFile.value)
  form.append('description', description.value)
  sending.value = true
  try {
    const response = await fetch('/api/intake/upload', { method: 'POST', body: form })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Upload failed')
    uploaded.value = data
    add('assistant', `I received ${data.filename}.\n\n${data.analysis}`)
  } catch (error) {
    add('assistant', error.message)
  } finally {
    sending.value = false
  }
}

async function send() {
  const text = message.value.trim()
  if (!text || sending.value) return
  message.value = ''
  add('user', text)
  sending.value = true
  try {
    const response = await fetch('/api/intake/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, project_summary: summary.value, media_notes: uploaded.value ? `${uploaded.value.filename}: ${description.value}` : '' }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Unable to analyze right now')
    add('assistant', data.reply)
  } catch (error) {
    add('assistant', `${error.message} We can still collect the details and arrange a meet-and-greet.`)
  } finally {
    sending.value = false
  }
}

async function book() {
  sending.value = true
  notice.value = ''
  try {
    const uploads = uploaded.value ? [{ upload_id: uploaded.value.upload_id, filename: uploaded.value.filename, media_type: uploaded.value.media_type, description: description.value }] : []
    const response = await fetch('/api/appointments/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...appointment.value, project_summary: summary.value || 'Customer requested an in-person meet-and-greet.', uploads, assumptions_confirmed: agreed.value }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Could not request appointment')
    notice.value = data.message
    projectCode.value = data.project_code || ''
    step.value = 'done'
  } catch (error) {
    notice.value = error.message
  } finally {
    sending.value = false
  }
}

async function lookupProject() {
  projectError.value = ''
  project.value = null
  if (!projectCode.value.trim() || !projectPhone.value.trim()) {
    projectError.value = 'Enter your project code and the phone number used for the request.'
    return
  }
  try {
    const query = new URLSearchParams({ code: projectCode.value.trim(), phone: projectPhone.value.trim() })
    const response = await fetch(`/api/projects/lookup?${query}`)
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Project not found')
    project.value = data
  } catch (error) {
    projectError.value = error.message
  }
}
</script>

<template>
  <main>
    <div class="utility-bar"><span>Northeast Ohio home projects</span><a :href="`tel:${phone}`">Call LODEX · {{ phone }}</a></div>
    <nav class="site-nav">
      <a class="brand" href="#top" aria-label="LODEX home"><strong>LODEX</strong><span>Construction · Maintenance · Repair</span></a>
      <div class="nav-links"><a href="#about">About</a><a href="#gallery">Gallery</a><a href="#project">My project</a></div>
      <button type="button" class="nav-cta" @click="openSchedule">Schedule a visit <span>↗</span></button>
    </nav>

    <section id="top" class="hero page-width">
      <div class="hero-copy">
        <p class="eyebrow">A better way to start a home project</p>
        <h1>Whatcha tryna <em>do?</em></h1>
        <p class="lede">Build. Fix. Upgrade or customize. Start with the idea, show us the space, and we’ll help turn it into a clear next step.</p>
        <div class="intent-row"><button v-for="intent in intents" :key="intent" type="button" class="intent" @click="chooseIntent(intent)">{{ intent }}</button></div>
        <div class="hero-actions"><button type="button" class="primary-button" @click="document.querySelector('#intake')?.scrollIntoView({ behavior: 'smooth' })">Start with your project <span>↗</span></button><a class="phone-link" :href="`tel:${phone}`">Or call {{ phone }}</a></div>
      </div>
      <div class="hero-collage" aria-label="LODEX project inspiration">
        <button v-for="(item, index) in galleryItems.slice(0, 3)" :key="item.title" type="button" class="collage-card" :class="`collage-${index + 1}`" @click="galleryOpen = item"><img :src="item.image" :alt="item.title" @error="imageFallback"/><span>{{ item.category }} <b>↗</b></span></button>
        <div class="collage-note"><span>Ideas welcome.</span><b>Details matter.</b></div>
      </div>
    </section>

    <section id="about" class="about-section page-width">
      <div class="section-kicker"><span>01</span><span>About LODEX</span></div>
      <div class="about-grid"><h2>Real work starts with a real conversation.</h2><div><p>LODEX helps homeowners move from “I’ve been meaning to fix that” to a clear, practical plan. Small jobs are welcome. Bigger ideas are welcome too.</p><p>We use photos, questions, and an in-person meet-and-greet to confirm the scope before a final price is set.</p><a class="text-link" href="#intake">Tell us what you have in mind →</a></div></div>
      <div class="about-points"><div><b>01</b><span>Listen first</span><small>We start with what you actually want—not a prewritten package.</small></div><div><b>02</b><span>Make it clear</span><small>Assumptions and unknowns stay visible before work begins.</small></div><div><b>03</b><span>Keep you close</span><small>Your project details and updates stay in one place.</small></div></div>
    </section>

    <section id="gallery" class="gallery-section">
      <div class="page-width"><div class="section-kicker light"><span>02</span><span>Possibilities</span></div><div class="gallery-heading"><div><p class="eyebrow">Concept inspiration from the LZ Custom archive</p><h2>See a direction.<br/><em>Then make it yours.</em></h2></div><p>These images are inspiration for what thoughtful fabrication, repair, and finishing can look like. Your space and your project are the source of truth.</p></div><div class="gallery-grid"><button v-for="item in galleryItems" :key="item.title" type="button" class="gallery-card" @click="galleryOpen = item"><div class="gallery-image"><img :src="item.image" :alt="item.title" loading="lazy" @error="imageFallback"/><span>View ↗</span></div><div class="gallery-meta"><span>{{ item.category }}</span><b>{{ item.title }}</b></div></button></div></div>
    </section>

    <section id="intake" class="intake-section">
      <div class="page-width"><div class="section-kicker light"><span>03</span><span>Start your project</span></div><div class="intake-head"><div><p class="eyebrow">No pressure. No made-up estimate.</p><h2>Let’s figure out<br/><em>what’s next.</em></h2></div><div class="scope-meter"><div class="scope-meter-top"><span>{{ scopeLabel }}</span><b>{{ scopePercent }}%</b></div><div class="meter-track"><i :style="{ width: `${scopePercent}%` }"></i></div><small>Scope confirmation reaches 100% when you confirm the working assumptions.</small></div></div>
        <div class="flow"><span :class="{ active: step === 'chat' }">1. Talk it through</span><span :class="{ active: step === 'schedule' }">2. Meet in person</span><span :class="{ active: step === 'done' }">3. Keep the details</span></div>
        <div v-if="step === 'chat'" class="workspace"><div class="chat-card"><div class="chat-title"><i></i><div><b>Project support</b><small>A human-friendly starting point, with AI help when useful.</small></div><button type="button" class="mini-link" @click="openSchedule">Schedule now ↗</button></div><div class="messages"><article v-for="(item, index) in messages" :key="index" :class="item.role"><p>{{ item.text }}</p></article><div v-if="sending" class="assistant"><p class="typing">Thinking through the project…</p></div></div><form class="composer" @submit.prevent="send"><textarea v-model="message" :disabled="sending" placeholder="For example: I need a TV mounted above a brick fireplace…" rows="3"></textarea><button type="submit" :disabled="sending || !message.trim()">Send</button></form></div>
          <aside class="upload-card"><p class="eyebrow">Helpful, not required</p><h3>Show us the work area.</h3><p>Photos and short videos help us ask better questions. They do not create a final estimate.</p><label class="file-picker"><input type="file" accept="image/jpeg,image/png,image/webp,image/heic,video/mp4,video/quicktime,video/webm" @change="selectedFile = $event.target.files[0]"/><span>{{ selectedFile ? selectedFile.name : 'Choose photo or video' }}</span><b>＋</b></label><textarea v-model="description" placeholder="Anything we should notice?"></textarea><button type="button" class="outline-button" @click="upload" :disabled="!selectedFile || sending">{{ sending ? 'Uploading…' : 'Upload & analyze' }}</button><label class="confirm"><input v-model="agreed" type="checkbox" :disabled="!hasCustomerMessage"/> <span>I reviewed the working assumptions and they are accurate to the best of my knowledge.</span></label><button type="button" class="ready-button" @click="openSchedule" :disabled="!canSchedule">Continue to meet-and-greet <span>↗</span></button></aside></div>
        <form v-else-if="step === 'schedule'" class="schedule-card" @submit.prevent="book"><div><p class="eyebrow">Next: a real-world check</p><h3>Request your meet-and-greet.</h3><p>Choose a preferred window. We’ll confirm the visit and clarify anything still unknown before a final price is set.</p></div><div class="fields"><input v-model="appointment.name" required placeholder="Your name"/><input v-model="appointment.phone" required placeholder="Phone"/><input v-model="appointment.email" type="email" placeholder="Email (optional)"/><input v-model="appointment.address" required placeholder="Job address"/><input v-model="appointment.preferred_date" required type="date"/><select v-model="appointment.preferred_time" required><option disabled value="">Preferred arrival window</option><option>Morning · 9 AM–12 PM</option><option>Afternoon · 12 PM–3 PM</option><option>Late afternoon · 3 PM–6 PM</option></select></div><div class="schedule-actions"><button type="submit" class="primary-button" :disabled="sending">{{ sending ? 'Sending…' : 'Request meet-and-greet' }} <span>↗</span></button><button type="button" class="back-button" @click="step = 'chat'">Back to conversation</button></div><p v-if="notice" class="notice">{{ notice }}</p></form>
        <div v-else class="success-card"><p class="eyebrow">Request received</p><h3>We’ll confirm the visit shortly.</h3><p>{{ notice }}</p><div v-if="projectCode" class="project-code"><span>Your project code</span><b>{{ projectCode }}</b><small>Save this code with the phone number you used. You can return to the project portal below.</small></div><a class="text-link" href="#project">Open my project details →</a></div>
      </div>
    </section>

    <section id="project" class="project-section page-width"><div class="section-kicker"><span>04</span><span>Returning customers</span></div><div class="project-grid"><div><p class="eyebrow">Your project, in one place</p><h2>Need the details<br/><em>again?</em></h2><p class="project-lede">Use the project code from your confirmation and the phone number on the request to see the latest scope, visit status, and next step.</p><a class="phone-link" :href="`tel:${phone}`">Need help finding it? Call {{ phone }}</a></div><form class="lookup-card" @submit.prevent="lookupProject"><label>Project code<input v-model="projectCode" placeholder="LDX-123456" autocomplete="off"/></label><label>Phone used for the request<input v-model="projectPhone" type="tel" placeholder="216-555-0123" autocomplete="tel"/></label><button type="submit" class="primary-button">Open my project <span>↗</span></button><p v-if="projectError" class="error">{{ projectError }}</p><div v-if="project" class="project-result"><div class="project-result-top"><span>{{ project.status }}</span><b>{{ project.progress }}%</b></div><h3>{{ project.title }}</h3><p>{{ project.next_step }}</p><div class="meter-track"><i :style="{ width: `${project.progress}%` }"></i></div><small>Scope confirmation: {{ project.scope_confirmed ? '100% confirmed' : 'still being reviewed' }}</small></div></form></div></section>

    <footer class="site-footer"><div class="footer-brand"><strong>LODEX</strong><span>Construction · Maintenance · Repair</span></div><div class="footer-links"><a href="#about">About</a><a href="#gallery">Gallery</a><a href="#intake">Start a project</a><a href="#project">My project</a></div><div class="footer-contact"><a :href="`tel:${phone}`">{{ phone }}</a><span>Northeast Ohio</span></div><div class="footer-bottom"><span>Clear scope. Thoughtful work. No surprises.</span><span>© 2026 LODEX</span></div></footer>

    <button type="button" class="support-fab" :class="{ open: supportOpen }" @click="openSupport" :aria-expanded="supportOpen"><span>{{ supportOpen ? '×' : '✦' }}</span>{{ supportOpen ? 'Close' : 'Need help?' }}</button>
    <div v-if="supportOpen" class="support-popover"><p class="eyebrow">LODEX support</p><h3>What do you need?</h3><button type="button" @click="chooseIntent('Fix'); supportOpen = false">Start a project</button><a :href="`tel:${phone}`" @click="supportOpen = false">Call {{ phone }}</a><button type="button" @click="openSchedule(); supportOpen = false">Request a meet-and-greet</button><form @submit.prevent="send(); supportOpen = false"><input v-model="message" class="support-input" placeholder="Ask a quick question…"/><button type="submit">Send</button></form></div>

    <div v-if="galleryOpen" class="lightbox" @click.self="galleryOpen = null"><button type="button" class="lightbox-close" @click="galleryOpen = null">×</button><img :src="galleryOpen.image" :alt="galleryOpen.title" @error="imageFallback"/><div><span>{{ galleryOpen.category }}</span><h3>{{ galleryOpen.title }}</h3><a href="#intake" @click="galleryOpen = null">Start with an idea like this →</a></div></div>
  </main>
</template>
