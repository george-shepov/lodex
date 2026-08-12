<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import packageMetadata from '../package.json'
import { lzGalleryProjects } from './lzGallery'

const phone = '(440) 601-8001'
const phoneHref = 'tel:+14406018001'
const step = ref('chat')
const message = ref('')
const description = ref('')
const selectedFile = ref(null)
const uploaded = ref(null)
const sending = ref(false)
const agreed = ref(false)
const intakeReady = ref(false)
const handoffMessage = ref('')
const qualification = ref({ progress: 0, qualified: false, label: '', requirements: [] })
const supportOpen = ref(false)
const projectCode = ref('')
const projectPhone = ref('')
const project = ref(null)
const projectError = ref('')
const currentPath = ref(window.location.pathname)
const selectedService = ref(null)
const virtualOpen = ref(false)
const virtualRoom = ref('')
const virtualStatus = ref('')
const virtualError = ref('')
const dualCamera = ref(false)
const cameraFacing = ref('environment')
const remoteConnected = ref(false)
const localVideoRef = ref(null)
const workVideoRef = ref(null)
const remoteVideoRef = ref(null)
let virtualSocket = null
let virtualPeer = null
let virtualStreams = []
const appointment = ref({ name: '', phone: '', email: '', address: '', preferred_date: '', preferred_time: '' })
const notice = ref('')
const paymentStatus = ref('not_started')
const paymentError = ref('')
const selectedInspiration = ref(null)
const galleryFilter = ref('All')
const galleryVisible = ref(24)

const services = [
  {
    slug: 'contracting-renovations',
    nav: 'Renovate',
    title: 'General Contracting & Renovations',
    short: 'Renovate',
    summary: 'Project management, structural updates, space remodels, and skilled-trade coordination.',
    intro: 'Bring the bigger picture. We help turn it into a practical plan, coordinate the right work, and keep the details moving.',
    includes: ['Room remodels and refreshes', 'Project planning and trade coordination', 'Structural and finish updates', 'Built-ins, cabinetry, and custom improvements'],
    useCases: ['Kitchen, bath, basement, and office upgrades', 'A property that needs a refresh before move-in', 'A larger scope that needs one clear point of coordination'],
    starter: 'I am planning a renovation or larger improvement. Here is what I want to change: ',
  },
  {
    slug: 'handyman-maintenance',
    nav: 'Repair & maintain',
    title: 'Handyman & Property Maintenance',
    short: 'Repair & maintain',
    summary: 'On-demand repairs, general upkeep, seasonal maintenance, and fixture updates for homes and businesses.',
    intro: 'The work that keeps a property working well—without turning a small issue into a weeks-long project.',
    includes: ['Repairs, adjustments, and punch lists', 'Fixture, hardware, and TV installation', 'Doors, trim, drywall, paint, and caulking', 'Seasonal and ongoing property care'],
    useCases: ['A list of fixes before guests, tenants, or a sale', 'A recurring maintenance partner', 'A repair you can show us in a photo or short video'],
    starter: 'I need help with a repair or maintenance item: ',
  },
  {
    slug: 'white-glove-installation',
    nav: 'Deliver & install',
    title: 'White-Glove Delivery & Installation',
    short: 'Deliver & install',
    summary: 'Pickup, delivery, assembly, placement, testing, and cleanup for high-value equipment and furnishings.',
    intro: 'We handle the last mile with care: the right item, in the right place, assembled, tested, and cleared of packaging.',
    includes: ['Furniture and commercial fixture assembly', 'Fitness equipment setup and placement', 'Appliance and electronics installation', 'Packaging and debris removal'],
    useCases: ['A new home, office, Airbnb, or gym setup', 'A delivery that needs skilled assembly', 'Heavy or high-attention equipment that needs a finished handoff'],
    starter: 'I need an item picked up, delivered, assembled, or installed: ',
  },
  {
    slug: 'shopping-sourcing',
    nav: 'Find & source',
    title: 'Shopping, Sourcing & Procurement',
    short: 'Find & source',
    summary: 'Materials sourcing, fixture selection, hardware pickup, and specialized product procurement.',
    intro: 'Need a matching part, the right fixture, or someone to collect materials and bring them to the job? Start with what you need done.',
    includes: ['Material and hardware pickup', 'Product research and option comparison', 'Fixture, part, and finish matching', 'Purchase coordination and job-site delivery'],
    useCases: ['You know the outcome but not the exact part', 'A project needs materials gathered before work starts', 'A business needs dependable local procurement support'],
    starter: 'I need help finding, picking up, or sourcing: ',
  },
  {
    slug: 'cleaning-restoration',
    nav: 'Clean & restore',
    title: 'Cleaning & Surface Restoration',
    short: 'Clean & restore',
    summary: 'Pressure washing, general cleanup, and laser cleaning for targeted restoration.',
    intro: 'From a fresh exterior to a delicate restoration job, we match the cleaning method to the surface and desired result.',
    includes: ['Exterior pressure washing', 'Move-in, project, and general cleanup', 'Laser cleaning for rust, coatings, and surface restoration'],
    useCases: ['House exterior, patio, driveway, or concrete cleaning', 'A property that needs a cleanup before its next use', 'Metal, masonry, or specialty surfaces needing careful restoration'],
    starter: 'I need cleaning or restoration help. The surface/item is: ',
  },
]

const laserProjects = [
  {
    title: 'Rust removal in tight detail',
    category: 'Metal restoration',
    description: 'A controlled laser pass lifts corrosion from a hinge without abrasive blasting.',
    video: '/portfolio/laser/rusted-hinge-laser-cleaning.mp4',
    poster: '/portfolio/laser/rusted-hinge-laser-cleaning.webp',
    featured: true,
  },
  {
    title: 'Paint lifted from metal',
    category: 'Coating removal',
    description: 'Paint removal demonstrated on a shaped metal surface with the working edge kept visible.',
    video: '/portfolio/laser/blue-metal-paint-removal.mp4',
    poster: '/portfolio/laser/blue-metal-paint-removal.webp',
  },
  {
    title: 'Fire residue on stone',
    category: 'Masonry restoration',
    description: 'A short field demonstration of laser cleaning on a smoke- and fire-marked stone surface.',
    video: '/portfolio/laser/stone-fire-residue-cleaning.mp4',
    poster: '/portfolio/laser/stone-fire-residue-cleaning.webp',
  },
  {
    title: 'Surface buildup on metal',
    category: 'Precision cleaning',
    description: 'A narrow pass removes surface contamination while preserving the panel geometry.',
    video: '/portfolio/laser/metal-panel-surface-cleaning.mp4',
    poster: '/portfolio/laser/metal-panel-surface-cleaning.webp',
  },
]

const inspirationProjects = lzGalleryProjects.slice(0, 12)

const messages = ref([{ role: 'assistant', text: 'What can LODEX take off your plate? Choose a service below, tell us in your own words, or show us the space.' }])
const activeService = computed(() => services.find(service => currentPath.value.replace(/\/$/, '') === `/services/${service.slug}`) || null)
const isInspirationPage = computed(() => currentPath.value.replace(/\/$/, '') === '/inspiration')
const galleryCategories = computed(() => ['All', ...new Set(lzGalleryProjects.map(project => project.category))])
const filteredGalleryProjects = computed(() => galleryFilter.value === 'All' ? lzGalleryProjects : lzGalleryProjects.filter(project => project.category === galleryFilter.value))
const visibleGalleryProjects = computed(() => filteredGalleryProjects.value.slice(0, galleryVisible.value))
const lightboxCollection = computed(() => isInspirationPage.value ? filteredGalleryProjects.value : inspirationProjects)
const summary = computed(() => messages.value.filter(item => item.role === 'user').map(item => item.text).join('\n'))
const hasCustomerMessage = computed(() => messages.value.some(item => item.role === 'user'))
const scopePercent = computed(() => agreed.value ? 100 : qualification.value.progress || 0)
const scopeLabel = computed(() => agreed.value ? 'Scope confirmed' : intakeReady.value ? 'Ready for the next step' : qualification.value.qualified ? 'Lead qualified · optional details' : hasCustomerMessage.value ? 'Qualifying the project' : 'Ready when you are')
const canSchedule = computed(() => hasCustomerMessage.value || uploaded.value)
const intakeTitle = computed(() => selectedService.value?.title || 'Your project')

function serviceHref(service) { return `/services/${service.slug}` }
function openInspiration(project) { selectedInspiration.value = project }
function openInspirationGallery() { navigate('/inspiration') }
function selectGalleryFilter(category) { galleryFilter.value = category; galleryVisible.value = 24 }
function add(role, text, kind = null) {
  messages.value.push({ role, text, ...(kind ? { kind } : {}) })
  nextTick(() => document.querySelector('.messages')?.scrollTo({ top: 99999, behavior: 'smooth' }))
}
function scrollToIntake() { document.querySelector('#intake')?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }
function goHome(hash = '') {
  navigate('/')
  if (hash) nextTick(() => document.querySelector(hash)?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}
function navigate(path) {
  window.history.pushState({}, '', path)
  currentPath.value = window.location.pathname
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function openService(service) { navigate(serviceHref(service)) }
function chooseService(service, focus = true) {
  selectedService.value = service
  message.value = service.starter
  step.value = 'chat'
  if (focus) {
    scrollToIntake()
    nextTick(() => document.querySelector('.composer textarea')?.focus())
  }
}
function startFromService(service) {
  chooseService(service, false)
  goHome()
  nextTick(() => {
    scrollToIntake()
    document.querySelector('.composer textarea')?.focus()
  })
}
function openSchedule() {
  if (!hasCustomerMessage.value && !uploaded.value) {
    step.value = 'chat'
    scrollToIntake()
    nextTick(() => document.querySelector('.composer textarea')?.focus())
    return
  }
  step.value = 'schedule'
  scrollToIntake()
}
function openSupport() {
  supportOpen.value = !supportOpen.value
  if (supportOpen.value) nextTick(() => document.querySelector('.support-input')?.focus())
}
async function readApiResponse(response, fallbackMessage) {
  const raw = await response.text()
  let data
  try { data = raw ? JSON.parse(raw) : {} } catch { throw new Error(`${fallbackMessage} The service returned an unexpected response (${response.status}).`) }
  if (!response.ok) throw new Error(data.detail || data.error || fallbackMessage)
  return data
}
async function upload() {
  if (!selectedFile.value) return
  const form = new FormData()
  form.append('file', selectedFile.value)
  form.append('description', description.value)
  form.append('service_category', selectedService.value?.title || '')
  sending.value = true
  try {
    const response = await fetch('/api/intake/upload', { method: 'POST', body: form })
    const data = await readApiResponse(response, 'Upload failed.')
    uploaded.value = data
    add('assistant', `I received ${data.filename}.\n\n${data.analysis}`)
  } catch (error) { add('assistant', error.message) } finally { sending.value = false }
}
async function send() {
  const text = message.value.trim()
  if (!text || sending.value) return
  message.value = ''
  add('user', text)
  sending.value = true
  try {
    const conversation = messages.value.slice(-24).map(item => ({ role: item.role, text: item.text, ...(item.kind ? { kind: item.kind } : {}) }))
    const response = await fetch('/api/intake/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, project_summary: summary.value, media_notes: uploaded.value ? `${uploaded.value.filename}: ${description.value}` : '', service_category: selectedService.value?.title || '', conversation }) })
    const data = await readApiResponse(response, 'Unable to continue the scope review.')
    add('assistant', data.reply, data.question_kind)
    if (data.qualification) qualification.value = data.qualification
    if (data.captured_address && !appointment.value.address) appointment.value.address = data.captured_address
    intakeReady.value = Boolean(data.ready_to_schedule)
    if (data.ready_to_schedule) {
      handoffMessage.value = data.reply
      nextTick(openSchedule)
    } else {
      handoffMessage.value = ''
    }
  } catch (error) { add('assistant', `${error.message} We can still collect the details and arrange a meet-and-greet.`) } finally { sending.value = false }
}
async function book() {
  sending.value = true
  notice.value = ''
  paymentStatus.value = 'not_started'
  paymentError.value = ''
  try {
    const uploads = uploaded.value ? [{ upload_id: uploaded.value.upload_id, filename: uploaded.value.filename, media_type: uploaded.value.media_type, description: description.value }] : []
    const response = await fetch('/api/appointments/request', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...appointment.value, project_summary: summary.value || 'Customer requested an in-person meet-and-greet.', service_category: selectedService.value?.title || 'General inquiry', uploads, assumptions_confirmed: agreed.value, intake_ready: qualification.value.qualified }) })
    const data = await readApiResponse(response, 'Could not request appointment.')
    notice.value = data.message
    projectCode.value = data.project_code || ''
    step.value = 'done'
  } catch (error) { notice.value = error.message } finally { sending.value = false }
}
async function startDeposit() {
  const checkoutPhone = projectPhone.value.trim() || appointment.value.phone.trim()
  if (!projectCode.value || !checkoutPhone) return
  sending.value = true
  paymentError.value = ''
  try {
    try { sessionStorage.setItem('lodex-payment-context', JSON.stringify({ project_code: projectCode.value, phone: checkoutPhone })) } catch {}
    const response = await fetch('/api/payments/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_code: projectCode.value, phone: checkoutPhone }),
    })
    const data = await readApiResponse(response, 'Could not start the deposit payment.')
    paymentStatus.value = data.status || 'checkout_created'
    if (data.checkout_url) window.location.assign(data.checkout_url)
  } catch (error) {
    paymentError.value = error.message
  } finally {
    sending.value = false
  }
}
async function lookupProject() {
  projectError.value = ''
  paymentError.value = ''
  project.value = null
  if (!projectCode.value.trim() || !projectPhone.value.trim()) { projectError.value = 'Enter your project code and the phone number used for the request.'; return }
  try {
    const query = new URLSearchParams({ code: projectCode.value.trim(), phone: projectPhone.value.trim() })
    const response = await fetch(`/api/projects/lookup?${query}`)
    project.value = await readApiResponse(response, 'Project not found.')
    paymentStatus.value = project.value.payment_status || 'not_started'
  } catch (error) { projectError.value = error.message }
}
async function handlePaymentReturn() {
  const params = new URLSearchParams(window.location.search)
  const payment = params.get('payment')
  if (!payment) return
  let context = {}
  try { context = JSON.parse(sessionStorage.getItem('lodex-payment-context') || '{}') } catch {}
  projectCode.value = params.get('project_code') || context.project_code || ''
  projectPhone.value = context.phone || ''
  window.history.replaceState({}, '', `${window.location.pathname}${window.location.hash}`)
  if (payment === 'cancelled') {
    paymentError.value = 'Payment was cancelled. No deposit was charged.'
    goHome('#project')
    return
  }
  if (payment !== 'success') return
  paymentStatus.value = 'payment_pending'
  notice.value = 'Payment received. We’re confirming the deposit now…'
  if (projectCode.value && projectPhone.value) {
    for (let attempt = 0; attempt < 5; attempt += 1) {
      await lookupProject()
      if (paymentStatus.value === 'paid') {
        notice.value = 'Deposit payment recorded.'
        try { sessionStorage.removeItem('lodex-payment-context') } catch {}
        break
      }
      if (attempt < 4) await new Promise(resolve => setTimeout(resolve, 1500))
    }
  }
  goHome('#project')
}
async function openVirtualMeet() {
  virtualRoom.value = projectCode.value.trim().toUpperCase() || project.value?.project_code || `LDX-${Math.random().toString(36).slice(2, 8).toUpperCase()}`
  virtualOpen.value = true
  virtualStatus.value = 'Preparing your camera and microphone…'
  virtualError.value = ''
  await nextTick()
  await prepareVirtualMedia()
  if (!virtualError.value) connectVirtualRoom()
}
async function prepareVirtualMedia() {
  if (!navigator.mediaDevices?.getUserMedia) { virtualError.value = 'This browser does not provide camera access. You can still call LODEX or request a regular visit.'; return }
  stopVirtualMedia()
  try {
    const workStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: true })
    virtualStreams = [workStream]
    cameraFacing.value = 'environment'
    const cameras = (await navigator.mediaDevices.enumerateDevices()).filter(device => device.kind === 'videoinput')
    if (cameras.length > 1) {
      const workDevice = workStream.getVideoTracks()[0]?.getSettings()?.deviceId
      const subjectCamera = cameras.find(device => device.deviceId !== workDevice) || cameras[1]
      try { virtualStreams.push(await navigator.mediaDevices.getUserMedia({ video: { deviceId: { exact: subjectCamera.deviceId } }, audio: false })); dualCamera.value = true } catch { dualCamera.value = false }
    }
    if (workVideoRef.value) workVideoRef.value.srcObject = workStream
    if (localVideoRef.value) localVideoRef.value.srcObject = virtualStreams[1] || workStream
    virtualStatus.value = dualCamera.value ? 'Both cameras are ready. Waiting for LODEX to join…' : 'Camera ready. Waiting for LODEX to join…'
  } catch (error) { virtualError.value = error.name === 'NotAllowedError' ? 'Camera or microphone permission was declined. Allow access in your browser settings, then try again.' : 'We could not start the camera on this device. You can still request a regular visit.' }
}
function connectVirtualRoom() {
  if (!virtualRoom.value || virtualError.value) return
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  virtualSocket = new WebSocket(`${protocol}//${window.location.host}/api/virtual/rooms/${encodeURIComponent(virtualRoom.value)}`)
  virtualPeer = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] })
  virtualStreams.flatMap(stream => stream.getTracks()).forEach(track => virtualPeer.addTrack(track, virtualStreams.find(stream => stream.getTracks().includes(track))))
  virtualPeer.ontrack = event => { remoteConnected.value = true; if (remoteVideoRef.value && event.streams[0]) remoteVideoRef.value.srcObject = event.streams[0] }
  virtualPeer.onicecandidate = event => { if (event.candidate && virtualSocket?.readyState === WebSocket.OPEN) virtualSocket.send(JSON.stringify({ type: 'ice-candidate', candidate: event.candidate })) }
  virtualSocket.onmessage = async event => {
    const data = JSON.parse(event.data)
    if (data.type === 'room-full') { virtualError.value = 'This virtual room already has two people. Call LODEX if you need another invite.'; return }
    if (data.type === 'joined') { virtualStatus.value = data.participants > 1 ? 'Connecting your virtual visit…' : 'Room ready. Waiting for LODEX to join…'; return }
    if (data.type === 'peer-joined') { const offer = await virtualPeer.createOffer(); await virtualPeer.setLocalDescription(offer); virtualSocket.send(JSON.stringify({ type: 'offer', offer })) }
    if (data.type === 'offer') { await virtualPeer.setRemoteDescription(data.offer); const answer = await virtualPeer.createAnswer(); await virtualPeer.setLocalDescription(answer); virtualSocket.send(JSON.stringify({ type: 'answer', answer })) }
    if (data.type === 'answer') await virtualPeer.setRemoteDescription(data.answer)
    if (data.type === 'ice-candidate' && data.candidate) await virtualPeer.addIceCandidate(data.candidate)
  }
  virtualSocket.onerror = () => { virtualError.value = 'The virtual room could not connect. Your project details are still saved.' }
}
async function switchVirtualCamera() {
  if (dualCamera.value || !navigator.mediaDevices?.getUserMedia) return
  const nextFacing = cameraFacing.value === 'environment' ? 'user' : 'environment'
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: nextFacing } }, audio: false })
    const oldStream = virtualStreams[0]
    const newTrack = stream.getVideoTracks()[0]
    const sender = virtualPeer?.getSenders().find(item => item.track?.kind === 'video')
    if (sender) await sender.replaceTrack(newTrack)
    oldStream?.getVideoTracks().forEach(track => track.stop())
    virtualStreams[0] = new MediaStream([newTrack, ...(oldStream?.getAudioTracks() || [])])
    if (workVideoRef.value) workVideoRef.value.srcObject = virtualStreams[0]
    if (localVideoRef.value) localVideoRef.value.srcObject = virtualStreams[0]
    cameraFacing.value = nextFacing
  } catch { virtualStatus.value = 'This phone did not allow the other camera. Keep the current camera or use the regular visit request.' }
}
async function copyVirtualInvite() {
  const invite = `${window.location.origin}/#project?code=${encodeURIComponent(virtualRoom.value)}`
  try { await navigator.clipboard.writeText(invite); virtualStatus.value = 'Room invite copied. Send it to the LODEX person joining you.' } catch { virtualStatus.value = `Room code: ${virtualRoom.value}` }
}
function stopVirtualMedia() {
  virtualStreams.flatMap(stream => stream.getTracks()).forEach(track => track.stop())
  virtualStreams = []
  if (virtualPeer) virtualPeer.close()
  if (virtualSocket) virtualSocket.close()
  virtualPeer = null; virtualSocket = null; remoteConnected.value = false; dualCamera.value = false
}
function closeVirtualMeet() { stopVirtualMedia(); virtualOpen.value = false; virtualStatus.value = ''; virtualError.value = '' }
function closeInspiration() { selectedInspiration.value = null }
function moveInspiration(direction) {
  const collection = lightboxCollection.value
  const index = collection.findIndex(project => project.src === selectedInspiration.value?.src)
  if (index < 0 || !collection.length) return
  selectedInspiration.value = collection[(index + direction + collection.length) % collection.length]
}
function onKeydown(event) {
  if (event.key === 'Escape') closeInspiration()
  if (selectedInspiration.value && event.key === 'ArrowLeft') moveInspiration(-1)
  if (selectedInspiration.value && event.key === 'ArrowRight') moveInspiration(1)
}
function onPopState() { currentPath.value = window.location.pathname }
onMounted(() => { window.addEventListener('popstate', onPopState); window.addEventListener('keydown', onKeydown); handlePaymentReturn() })
onBeforeUnmount(() => { window.removeEventListener('popstate', onPopState); window.removeEventListener('keydown', onKeydown); stopVirtualMedia() })
</script>

<template>
  <main>
    <div class="utility-bar"><span>Northeast Ohio · Residential & commercial</span><a :href="phoneHref">Call LODEX · {{ phone }}</a></div>
    <nav class="site-nav" aria-label="Primary navigation">
      <a class="brand" href="/" @click.prevent="goHome" aria-label="LODEX home"><img class="brand-logo" src="/lodex-logo-blended.svg" alt="LODEX Residential & Commercial Services" /></a>
      <div class="nav-links"><a href="/#services" @click.prevent="goHome('#services')">Services</a><a href="/inspiration" @click.prevent="openInspirationGallery">Inspiration</a><a href="/#how-it-works" @click.prevent="goHome('#how-it-works')">How it works</a><a href="/#project" @click.prevent="goHome('#project')">My project</a></div>
      <button type="button" class="nav-cta" @click="goHome(); nextTick(openSchedule)">Start a project <span>↗</span></button>
    </nav>

    <template v-if="activeService">
      <section class="service-hero page-width">
        <a class="back-link" href="/" @click.prevent="goHome">← All services</a>
        <p class="eyebrow">LODEX services / {{ activeService.short }}</p>
        <div class="service-hero-grid">
          <div><h1>{{ activeService.title }}</h1><p class="service-lede">{{ activeService.intro }}</p><div class="hero-actions"><button type="button" class="primary-button" @click="startFromService(activeService)">Start this project <span>↗</span></button><a class="phone-link" :href="phoneHref">Call {{ phone }}</a></div></div>
          <aside class="service-callout"><span>What we handle</span><b>{{ activeService.summary }}</b><small>Tell us the outcome you want. We’ll confirm the right scope before any final price is set.</small></aside>
        </div>
      </section>
      <section class="service-details page-width"><div><p class="section-kicker">Included services</p><ul><li v-for="item in activeService.includes" :key="item">{{ item }}</li></ul></div><div><p class="section-kicker">A good fit when</p><ul><li v-for="item in activeService.useCases" :key="item">{{ item }}</li></ul></div></section>
      <section v-if="activeService.slug === 'cleaning-restoration'" class="laser-showcase laser-showcase-service">
        <div class="page-width"><div class="section-heading"><div><p class="eyebrow">Real laser-cleaning footage</p><h2>Watch the surface change.</h2></div><p>Short field demonstrations from our laser-restoration partner. Every project still begins with a material and finish review.</p></div><div class="laser-grid"><article v-for="project in laserProjects" :key="project.video" class="laser-card"><video :autoplay="project.featured" muted loop playsinline controls preload="metadata" :poster="project.poster" :aria-label="project.title"><source :src="project.video" type="video/mp4"/></video><div><span>{{ project.category }}</span><h3>{{ project.title }}</h3><p>{{ project.description }}</p></div></article></div></div>
      </section>
      <section class="service-next"><div class="page-width"><p class="eyebrow">Start with the real details</p><h2>Photo, video, or a few plain words is enough to begin.</h2><button type="button" class="primary-button" @click="startFromService(activeService)">Tell us about it <span>↗</span></button></div></section>
    </template>

    <template v-else-if="isInspirationPage">
      <section class="gallery-hero page-width">
        <a class="back-link" href="/" @click.prevent="goHome">← LODEX home</a>
        <p class="eyebrow">LZ Custom inspiration archive</p>
        <div class="gallery-hero-grid">
          <div><h1>Find the detail that starts your project.</h1></div>
          <div><b>{{ lzGalleryProjects.length }} unique concepts</b><p>This is an AI-generated inspiration library—not a claim of completed LODEX work. Save an idea, show us your real space, and we’ll help translate the direction into a practical scope.</p></div>
        </div>
      </section>
      <section class="gallery-browser page-width">
        <div class="gallery-toolbar" aria-label="Filter inspiration gallery">
          <button v-for="category in galleryCategories" :key="category" type="button" :class="{ active: galleryFilter === category }" @click="selectGalleryFilter(category)">{{ category }}<span>{{ category === 'All' ? lzGalleryProjects.length : lzGalleryProjects.filter(project => project.category === category).length }}</span></button>
        </div>
        <p class="gallery-status">Showing {{ visibleGalleryProjects.length }} of {{ filteredGalleryProjects.length }} concepts</p>
        <div class="archive-grid">
          <figure v-for="project in visibleGalleryProjects" :key="project.id" tabindex="0" role="button" :aria-label="`View ${project.title}`" @click="openInspiration(project)" @keydown.enter="openInspiration(project)" @keydown.space.prevent="openInspiration(project)">
            <img :src="project.src" :alt="project.alt" loading="lazy" decoding="async"/>
            <figcaption><span>{{ project.category }}</span><b>{{ project.title }}</b></figcaption>
          </figure>
        </div>
        <button v-if="visibleGalleryProjects.length < filteredGalleryProjects.length" type="button" class="gallery-more" @click="galleryVisible += 24">Show 24 more <span>↘</span></button>
      </section>
      <section class="gallery-cta"><div class="page-width"><p class="eyebrow">Turn inspiration into a real scope</p><h2>Show us the idea and the space you actually have.</h2><button type="button" class="primary-button" @click="goHome('#intake')">Start your project <span>↗</span></button></div></section>
    </template>

    <template v-else>
      <section id="top" class="hero page-width">
        <div class="hero-copy"><p class="eyebrow">LODEX Home Services</p><h1>Whatcha tryna <em>do?</em></h1><p class="lede">Renovate. Repair & maintain. Deliver & install. Find & source. Clean & restore. Choose the kind of help you need, or tell us the whole project in your own words.</p><div class="hero-service-lanes" aria-label="Choose a LODEX service"><button v-for="service in services" :key="service.slug" type="button" @click="chooseService(service); scrollToIntake()">{{ service.nav }}</button></div><div class="hero-actions"><button type="button" class="primary-button" @click="scrollToIntake">Start with your project <span>↗</span></button><a class="phone-link" :href="phoneHref">Or call {{ phone }}</a></div></div>
        <div class="hero-visual" aria-label="LODEX project examples"><video class="hero-background-video" autoplay muted loop playsinline preload="metadata" poster="/inspiration/custom-cabinetry.png" aria-label="LODEX project showcase"><source src="/lodex-hero.mp4" type="video/mp4"/></video><div class="hero-video-scrim"></div></div>
      </section>

      <section id="inspiration" class="inspiration-section page-width"><div class="section-heading"><div><p class="eyebrow">LZ Custom inspiration · {{ lzGalleryProjects.length }} concepts</p><h2>See what thoughtful work can look like.</h2></div><div class="inspiration-intro"><button type="button" class="text-button" @click="openInspirationGallery">Explore all {{ lzGalleryProjects.length }} concepts →</button></div></div><div class="inspiration-grid"><figure v-for="project in inspirationProjects" :key="project.src" tabindex="0" role="button" :aria-label="`View ${project.title}`" @click="openInspiration(project)" @keydown.enter="openInspiration(project)" @keydown.space.prevent="openInspiration(project)"><img :src="project.src" :alt="project.title" loading="lazy"/><figcaption><b>{{ project.title }}</b><span>{{ project.detail }}</span></figcaption></figure></div><button type="button" class="gallery-more gallery-more-home" @click="openInspirationGallery">Open the complete inspiration archive <span>↗</span></button></section>

      <section id="services" class="services-section page-width"><div class="section-heading"><div><p class="eyebrow">LODEX services</p><h2>Renovate, repair, deliver, source, and restore.</h2></div><p>Five clear ways to start. Every service begins with a practical look at scope, access, timing, materials, and the next step.</p></div><div class="service-grid"><a v-for="(service, index) in services" :key="service.slug" class="service-card" :href="serviceHref(service)" @click.prevent="openService(service)"><span>0{{ index + 1 }}</span><h3>{{ service.title }}</h3><p>{{ service.summary }}</p><b>Explore service →</b></a></div></section>

      <section id="laser-restoration" class="laser-showcase"><div class="page-width"><div class="section-heading"><div><p class="eyebrow">LODEX × Cyber Carp</p><h2>Laser restoration you can see.</h2></div><p>Rust, paint, surface buildup, and fire residue—shown in real working clips, not stock footage.</p></div><div class="laser-grid"><article v-for="project in laserProjects" :key="project.video" class="laser-card"><video :autoplay="project.featured" muted loop playsinline controls preload="metadata" :poster="project.poster" :aria-label="project.title"><source :src="project.video" type="video/mp4"/></video><div><span>{{ project.category }}</span><h3>{{ project.title }}</h3><p>{{ project.description }}</p></div></article></div><div class="laser-showcase-actions"><button type="button" class="primary-button" @click="openService(services[4])">Explore cleaning & restoration <span>↗</span></button><button type="button" class="text-button" @click="chooseService(services[4]); scrollToIntake()">Show us your surface →</button></div></div></section>

      <section id="how-it-works" class="how-section"><div class="page-width"><p class="eyebrow">Simple by design</p><div class="how-grid"><h2>Clear scope before the work begins.</h2><div class="how-steps"><div><b>01</b><h3>Tell us the outcome</h3><p>Choose a service, describe the job, or send photos and short video.</p></div><div><b>02</b><h3>Confirm the real details</h3><p>We ask only what is needed to understand scope, access, timing, and materials.</p></div><div><b>03</b><h3>Set the next step</h3><p>Request a meet-and-greet or coordinated visit—then get a clear, confirmed plan.</p></div></div></div></div></section>

      <section id="intake" class="intake-section"><div class="page-width"><div class="intake-head"><div><p class="eyebrow">Start your project</p><h2>Let’s figure out <em>what’s next.</em></h2><p class="intake-copy">Selected service: <b>{{ intakeTitle }}</b></p></div><div class="scope-meter"><div class="scope-meter-top"><span>{{ scopeLabel }}</span><b>{{ scopePercent }}%</b></div><div class="meter-track"><i :style="{ width: `${scopePercent}%` }"></i></div><small>{{ qualification.qualified ? 'The required facts are covered; useful extras can still improve the visit.' : 'Progress reflects the service facts we actually need—not the number of messages.' }}</small></div></div>
        <div class="service-chips" aria-label="Choose a service"><button v-for="service in services" :key="service.slug" type="button" :class="{ selected: selectedService?.slug === service.slug }" @click="chooseService(service, false)">{{ service.short }}</button></div>
        <div class="flow"><span :class="{ active: step === 'chat' }">1. Talk it through</span><span :class="{ active: step === 'schedule' }">2. Request a visit</span><span :class="{ active: step === 'done' }">3. Keep the details</span></div>
        <div v-if="step === 'chat'" class="workspace"><div class="chat-card"><div class="chat-title"><i></i><div><b>LODEX project intake</b><small>Human-friendly questions, with AI help when useful.</small></div><button type="button" class="mini-link" @click="openSchedule">Request a visit ↗</button></div><div class="messages"><article v-for="(item, index) in messages" :key="index" :class="item.role"><p>{{ item.text }}</p></article><div v-if="sending" class="assistant"><p class="typing">Thinking through the project…</p></div></div><form class="composer" @submit.prevent="send"><textarea v-model="message" :disabled="sending" placeholder="For example: I need a TV mounted above a brick fireplace…" rows="3"></textarea><button type="submit" :disabled="sending || !message.trim()">Send</button></form></div>
          <aside class="upload-card"><p class="eyebrow">Helpful, not required</p><h3>Show us the work area.</h3><p>Photos and short videos help us ask better questions. They do not create a final estimate.</p><label class="file-picker"><input type="file" accept="image/jpeg,image/png,image/webp,image/heic,video/mp4,video/quicktime,video/webm" @change="selectedFile = $event.target.files[0]"/><span>{{ selectedFile ? selectedFile.name : 'Choose photo or video' }}</span><b>＋</b></label><textarea v-model="description" placeholder="Anything we should notice?"></textarea><button type="button" class="outline-button" @click="upload" :disabled="!selectedFile || sending">{{ sending ? 'Uploading…' : 'Upload & analyze' }}</button><div v-if="qualification.requirements.length" class="qualification-checklist"><small>{{ qualification.label }}</small><ul><li v-for="item in qualification.requirements" :key="item.id" :class="{ covered: item.covered }"><span>{{ item.covered ? '✓' : '○' }}</span>{{ item.label }}</li></ul></div><label class="confirm"><input v-model="agreed" type="checkbox" :disabled="!hasCustomerMessage"/><span>I reviewed the captured scope and it is accurate to the best of my knowledge.</span></label><button type="button" class="ready-button" @click="openSchedule" :disabled="!canSchedule">{{ qualification.qualified ? 'Choose a visit time' : 'Continue to meet-and-greet' }} <span>↗</span></button></aside></div>
        <form v-else-if="step === 'schedule'" class="schedule-card" @submit.prevent="book"><div><p class="eyebrow">Next: a real-world check</p><h3>Request your meet-and-greet.</h3><p>{{ handoffMessage || 'Choose a preferred window. We’ll confirm the visit and clarify anything still unknown before a final price is set.' }}</p></div><div class="fields"><input v-model="appointment.name" required placeholder="Your name"/><input v-model="appointment.phone" required placeholder="Phone"/><input v-model="appointment.email" type="email" placeholder="Email (optional)"/><input v-model="appointment.address" required placeholder="Job address"/><input v-model="appointment.preferred_date" required type="date"/><select v-model="appointment.preferred_time" required><option disabled value="">Preferred arrival window</option><option>Morning · 9 AM–12 PM</option><option>Afternoon · 12 PM–3 PM</option><option>Late afternoon · 3 PM–6 PM</option></select></div><div class="schedule-actions"><button type="submit" class="primary-button" :disabled="sending">{{ sending ? 'Sending…' : 'Request meet-and-greet' }} <span>↗</span></button><button type="button" class="back-button" @click="step = 'chat'">Back to conversation</button></div><p v-if="notice" class="notice">{{ notice }}</p></form>
        <div v-else class="success-card"><p class="eyebrow">Request received</p><h3>We’ll confirm the visit shortly.</h3><p>{{ notice }}</p><div v-if="projectCode" class="project-code"><span>Your project code</span><b>{{ projectCode }}</b><small>Save this code with the phone number you used. You can return to the project portal below.</small></div><div v-if="paymentStatus === 'paid'" class="payment-confirmed">Deposit payment recorded.</div><button v-else type="button" class="primary-button" @click="startDeposit" :disabled="sending">{{ sending ? 'Opening secure checkout…' : 'Pay a requested deposit' }} <span>↗</span></button><p v-if="paymentError" class="error">{{ paymentError }}</p><a class="text-link" href="#project">Open my project details →</a></div>
      </div></section>

      <section id="project" class="project-section page-width"><div class="section-heading"><div><p class="eyebrow">Returning customers</p><h2>Your project, in one place.</h2></div><p>Use your project code and the phone number on the request to see the latest scope and next step.</p></div><form class="lookup-card" @submit.prevent="lookupProject"><label>Project code<input v-model="projectCode" placeholder="LDX-123456" autocomplete="off"/></label><label>Phone used for the request<input v-model="projectPhone" type="tel" placeholder="216-555-0123" autocomplete="tel"/></label><button type="submit" class="primary-button">Open my project <span>↗</span></button><p v-if="projectError" class="error">{{ projectError }}</p><div v-if="project" class="project-result"><div class="project-result-top"><span>{{ project.status }}</span><b>{{ project.progress }}%</b></div><h3>{{ project.title }}</h3><p v-if="project.service_category" class="project-service">{{ project.service_category }}</p><p>{{ project.next_step }}</p><div class="meter-track"><i :style="{ width: `${project.progress}%` }"></i></div><small>Scope confirmation: {{ project.scope_confirmed ? '100% confirmed' : 'still being reviewed' }}</small><div v-if="paymentStatus === 'paid'" class="payment-confirmed">Deposit payment recorded.</div><button v-else type="button" class="primary-button" @click="startDeposit" :disabled="sending">{{ sending ? 'Opening secure checkout…' : 'Pay a requested deposit' }} <span>↗</span></button><p v-if="paymentError" class="error">{{ paymentError }}</p><button type="button" class="virtual-button" @click="openVirtualMeet">▣ Start virtual meet-and-greet</button></div></form></section>
    </template>

    <div v-if="selectedInspiration" class="inspiration-lightbox" role="dialog" aria-modal="true" :aria-label="selectedInspiration.title" @click.self="closeInspiration"><button type="button" class="lightbox-close inspiration-lightbox-close" aria-label="Close image" @click="closeInspiration">×</button><button type="button" class="lightbox-arrow lightbox-previous" aria-label="Previous image" @click="moveInspiration(-1)">←</button><img :src="selectedInspiration.src" :alt="selectedInspiration.alt || selectedInspiration.title"/><button type="button" class="lightbox-arrow lightbox-next" aria-label="Next image" @click="moveInspiration(1)">→</button><div><span>{{ selectedInspiration.category || 'AI inspiration concept' }}</span><b>{{ selectedInspiration.title }}</b><small>{{ selectedInspiration.detail }}</small></div></div>

    <footer class="site-footer"><div class="footer-shell"><section class="footer-intro"><a class="footer-brand-link" href="/" @click.prevent="goHome"><img class="footer-logo" src="/lodex-logo-blended.svg" alt="LODEX Residential & Commercial Services"/></a><p>One practical partner for property projects across Northeast Ohio—from sourcing to the finished walkthrough.</p></section><nav class="footer-group"><span>Services</span><a v-for="service in services" :key="service.slug" :href="serviceHref(service)" @click.prevent="openService(service)">{{ service.short }}</a></nav><nav class="footer-group"><span>Your project</span><a href="/inspiration" @click.prevent="openInspirationGallery">Inspiration archive</a><a href="/#intake" @click.prevent="goHome('#intake')">Start a project</a><a href="/#project" @click.prevent="goHome('#project')">Open my project</a><a :href="phoneHref">Call {{ phone }}</a></nav><div class="footer-bottom"><span>© {{ new Date().getFullYear() }} LODEX · v{{ packageMetadata.version }}</span><span>Clear scope. Thoughtful work. No surprises.</span></div></div></footer>

    <button type="button" class="support-fab" :class="{ open: supportOpen }" @click="openSupport" :aria-expanded="supportOpen"><span>{{ supportOpen ? '×' : '✦' }}</span>{{ supportOpen ? 'Close' : 'Need help?' }}</button>
    <div v-if="supportOpen" class="support-popover"><p class="eyebrow">LODEX support</p><h3>What do you need?</h3><button v-for="service in services" :key="service.slug" type="button" @click="chooseService(service); supportOpen = false">{{ service.short }}</button><a :href="phoneHref" @click="supportOpen = false">Call {{ phone }}</a><form @submit.prevent="send(); supportOpen = false"><input v-model="message" class="support-input" placeholder="Ask a quick question…"/><button type="submit">Send</button></form></div>
    <div v-if="virtualOpen" class="virtual-modal" role="dialog" aria-modal="true" aria-label="Virtual meet-and-greet"><div class="virtual-header"><div><p class="eyebrow">LODEX virtual visit</p><h3>Meet from where the work is.</h3></div><button type="button" class="lightbox-close virtual-close" @click="closeVirtualMeet">×</button></div><div class="call-stage"><div class="remote-stage"><video ref="remoteVideoRef" autoplay playsinline></video><div v-if="!remoteConnected" class="waiting-state"><span>Waiting for LODEX to join</span><small>Room {{ virtualRoom }}</small></div><span class="video-label">LODEX</span></div><div class="local-stage"><div class="local-tile"><video ref="workVideoRef" autoplay playsinline muted></video><span>Work area</span></div><div class="local-tile"><video ref="localVideoRef" autoplay playsinline muted></video><span>You</span></div></div></div><p v-if="virtualStatus" class="virtual-status">{{ virtualStatus }}</p><p v-if="virtualError" class="virtual-error">{{ virtualError }}</p><div class="virtual-actions"><button v-if="!dualCamera" type="button" class="outline-button" @click="switchVirtualCamera">Switch camera</button><button type="button" class="outline-button" @click="copyVirtualInvite">Copy room invite</button><a class="primary-button" :href="phoneHref">Call LODEX</a><button type="button" class="back-button" @click="closeVirtualMeet">End virtual visit</button></div><small class="virtual-note">Your browser controls camera access. Dual-camera mode is attempted when the phone exposes two simultaneous camera devices; some mobile browsers allow only one camera at a time.</small></div>
  </main>
</template>
