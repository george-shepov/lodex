<script setup>
import { computed, nextTick, ref } from 'vue'

const step = ref('chat')
const message = ref('')
const description = ref('')
const selectedFile = ref(null)
const uploaded = ref(null)
const sending = ref(false)
const agreed = ref(false)
const appointment = ref({ name: '', phone: '', email: '', address: '', preferred_date: '', preferred_time: '' })
const notice = ref('')
const messages = ref([
  { role: 'assistant', text: 'What are you trying to build or fix? Describe it in your own words—or upload a photo or video and we’ll work through the details together.' },
])
const summary = computed(() => messages.value.filter(x => x.role === 'user').map(x => x.text).join('\n'))
const canConfirm = computed(() => messages.value.some(x => x.role === 'assistant' && x.text !== messages.value[0].text) && messages.value.some(x => x.role === 'user'))
const intents = ['Build', 'Fix', 'Upgrade', 'Customize']

function add(role, text) { messages.value.push({ role, text }); nextTick(() => document.querySelector('.messages')?.scrollTo({ top: 99999, behavior: 'smooth' })) }
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
async function upload() {
  if (!selectedFile.value) return
  const form = new FormData(); form.append('file', selectedFile.value); form.append('description', description.value)
  sending.value = true
  try {
    const r = await fetch('/api/intake/upload', { method: 'POST', body: form }); const data = await r.json()
    if (!r.ok) throw new Error(data.detail || 'Upload failed')
    uploaded.value = data; add('assistant', `I received ${data.filename}.\n\n${data.analysis}`)
  } catch (e) { add('assistant', e.message) } finally { sending.value = false }
}
async function send() {
  const text = message.value.trim(); if (!text || sending.value) return
  message.value = ''; add('user', text); sending.value = true
  try {
    const r = await fetch('/api/intake/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, project_summary: summary.value, media_notes: uploaded.value ? `${uploaded.value.filename}: ${description.value}` : '' }) })
    const data = await r.json(); if (!r.ok) throw new Error(data.detail || 'Unable to analyze right now')
    add('assistant', data.reply)
  } catch (e) { add('assistant', `${e.message} We can still collect the details and arrange a meet-and-greet.`) } finally { sending.value = false }
}
function readyToSchedule() { if (!agreed.value) return; step.value = 'schedule'; add('assistant', 'Great. Select a preferred day and time for a meet-and-greet. The appointment is requested—not final—until we confirm the visit and final scope.') }
async function book() {
  sending.value = true; notice.value = ''
  try {
    const uploads = uploaded.value ? [{ upload_id: uploaded.value.upload_id, filename: uploaded.value.filename, media_type: uploaded.value.media_type, description: description.value }] : []
    const r = await fetch('/api/appointments/request', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...appointment.value, project_summary: summary.value, uploads, assumptions_confirmed: agreed.value }) }); const data = await r.json()
    if (!r.ok) throw new Error(data.detail || 'Could not request appointment')
    notice.value = data.message; step.value = 'done'
  } catch (e) { notice.value = e.message } finally { sending.value = false }
}
</script>

<template>
  <main>
    <nav><strong>LODEX</strong><span>Build · Fix · Upgrade · Customize</span><a href="#intake">Start your project</a></nav>
    <section class="hero"><p class="eyebrow">Northeast Ohio home projects</p><h1>Whatcha tryna <em>do?</em></h1><p class="lede">Start with the goal. Then show us the space, talk it through, and confirm the details before we set a meet-and-greet.</p><div class="intent-row"><button v-for="intent in intents" :key="intent" class="intent" @click="chooseIntent(intent)">{{ intent }}</button></div><p class="microcopy">Build it. Fix it. Upgrade it. Make it yours.</p></section>
    <section class="inspiration"><img src="/inspiration/what-is-possible.png" alt="Concept examples of built-ins, refreshed interiors, a TV upgrade, and a custom wood entry"/><div><p class="eyebrow">What’s possible</p><h2>Bring the idea. We’ll help turn it into a plan.</h2><p>Concept inspiration—not a claim of past customer work. Upload the space you actually have, and the intake will narrow the next practical step.</p><button class="text-link" @click="chooseIntent('Customize')">Explore a custom idea →</button></div></section>
    <section id="intake" class="intake"><div class="flow"><span :class="{active:step==='chat'}">1. Understand</span><span :class="{active:step==='schedule'}">2. Meet</span><span :class="{active:step==='done'}">3. Confirm</span></div>
      <div v-if="step === 'chat'" class="workspace"><div class="chat"><div class="chat-title"><i></i><div><b>Project intake</b><small>We verify the scope before a final price.</small></div></div><div class="messages"><article v-for="(item,i) in messages" :key="i" :class="item.role"><p>{{ item.text }}</p></article><div v-if="sending" class="assistant"><p class="typing">Thinking through the project…</p></div></div><form @submit.prevent="send" class="composer"><textarea v-model="message" :disabled="sending" placeholder="For example: I need a TV mounted above a brick fireplace…" rows="3"></textarea><button :disabled="sending || !message.trim()">Send</button></form></div>
        <aside class="upload"><p class="eyebrow">Helpful, not required</p><h2>Show us the work area.</h2><p>Photos and short videos help us ask better questions. They do not create a final estimate.</p><label class="file"><input type="file" accept="image/jpeg,image/png,image/webp,image/heic,video/mp4,video/quicktime,video/webm" @change="selectedFile=$event.target.files[0]"/><span>{{ selectedFile ? selectedFile.name : 'Choose photo or video' }}</span></label><textarea v-model="description" placeholder="Anything we should notice in the image or video?"></textarea><button class="outline" @click="upload" :disabled="!selectedFile || sending">{{ sending ? 'Uploading…' : 'Upload & analyze' }}</button><label class="confirm"><input v-model="agreed" type="checkbox" :disabled="!canConfirm"/> I reviewed the discussion and confirm the working assumptions are accurate to the best of my knowledge.</label><button class="ready" @click="readyToSchedule" :disabled="!agreed">Continue to meet-and-greet →</button></aside></div>
      <form v-else-if="step === 'schedule'" @submit.prevent="book" class="schedule"><p class="eyebrow">Next: a real-world check</p><h2>Request your meet-and-greet.</h2><p>We will confirm the scope in person and then confirm the final price. Your requested time is held only after LODEX replies.</p><div class="fields"><input v-model="appointment.name" required placeholder="Your name"/><input v-model="appointment.phone" required placeholder="Phone"/><input v-model="appointment.email" type="email" placeholder="Email (optional)"/><input v-model="appointment.address" required placeholder="Job address"/><input v-model="appointment.preferred_date" required type="date"/><select v-model="appointment.preferred_time" required><option disabled value="">Preferred arrival window</option><option>Morning (9 AM–12 PM)</option><option>Afternoon (12 PM–3 PM)</option><option>Late afternoon (3 PM–6 PM)</option></select></div><button class="cta" :disabled="sending">{{ sending ? 'Sending…' : 'Request meet-and-greet' }}</button><p v-if="notice" class="notice">{{ notice }}</p></form>
      <div v-else class="schedule done"><p class="eyebrow">Request received</p><h2>We’ll confirm the visit shortly.</h2><p>{{ notice }}</p></div>
    </section>
    <section class="services"><p class="eyebrow">Small jobs welcome</p><h2>Clear work categories. A real person confirms the scope.</h2><div class="service-grid"><article><b>Mounting & assembly</b><span>TVs, shelving, furniture, hardware, smart-home devices.</span></article><article><b>Repair & adjustment</b><span>Doors, cabinets, fixtures, caulking, drywall and touch-ups.</span></article><article><b>Home upkeep</b><span>Property-maintenance lists, seasonal fixes and the small jobs larger contractors decline.</span></article><article><b>Project support</b><span>Photo/video intake first; then a meet-and-greet before a final price.</span></article></div><p class="area"><b>Serving Cleveland’s east side and surrounding communities.</b> Tell us the job address early so we can confirm that the visit fits the service area.</p></section>
    <section class="proof"><p class="eyebrow">How we earn the proof</p><h2>No made-up reviews. Every completed project becomes a documented before/after story—with customer permission.</h2><p>That gives new customers real work to judge, and it gives LODEX an honest portfolio and review base as projects are completed.</p></section>
    <footer>LODEX Construction Maintenance and Repair <span>•</span> Northeast Ohio <span>•</span> Final price is confirmed after scope validation.</footer>
  </main>
</template>

<style scoped>
.intent-row { display:flex; justify-content:center; flex-wrap:wrap; gap:10px; margin:28px auto 15px; }
.intent { min-width:112px; background:#fff; color:#141b22; border:1px solid #141b22; border-radius:999px; transition:transform .18s ease, background .18s ease, color .18s ease; }
.intent:hover,.intent:focus-visible { background:#141b22; color:#fff; transform:translateY(-2px); }
.microcopy { color:#716b63; font-size:14px; margin:0; }
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
@media(max-width:760px){ .inspiration { grid-template-columns:1fr; margin:0; }.inspiration img { min-height:220px; }.inspiration > div { padding:36px 24px; } }
@media(max-width:640px){ .service-grid { grid-template-columns:1fr; }.intent { min-width:calc(50% - 8px); } }
</style>
