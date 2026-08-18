<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import packageMetadata from '../package.json'
import { lzGalleryProjects } from './lzGallery'
import AdminPanel from './components/AdminPanel.vue'
import { serializeConversation } from './conversationPayload.mjs'
import { readStoredHomeProjectSize, readStoredSegment, SEGMENT_LABELS } from './segmentState.mjs'

const phone = '(440) 601-8001'
const phoneHref = 'tel:+14406018001'
const step = ref('chat')
const message = ref('')
const description = ref('')
const selectedFile = ref(null)
const uploaded = ref(null)
const sending = ref(false)
const chatSending = ref(false)
const uploadSending = ref(false)
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
const confirmation = ref(null)
const paymentStatus = ref('not_started')
const paymentError = ref('')
const selectedInspiration = ref(null)
const galleryFilter = ref('All')
const galleryVisible = ref(24)
const galleryLoading = ref(false)
const gallerySentinel = ref(null)
const hiddenGallerySources = ref(new Set())
const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || false
const homeReelPaused = ref(prefersReducedMotion)
const homeHeroSlideIndex = ref(0)
const homeVideoRef = ref(null)
const serviceReelPaused = ref(prefersReducedMotion)
const serviceHeroSlideIndex = ref(0)
const serviceHeroSlides = ref([])
let homeReelTimer = null
let serviceReelTimer = null
let galleryObserver = null
let presenceTimer = null
const visitorId = ref('')
const supportRequest = ref({ name: '', phone: '', message: '' })
const supportStatus = ref('')
const customerSegment = ref(readStoredSegment())
const homeProjectSize = ref(readStoredHomeProjectSize())

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
    heroImages: [
      { src: '/services/renovation-project-planning.webp', alt: 'LODEX renovation professional reviewing plans and finish samples inside a home', position: 'center center' },
    ],
    galleryCategories: ['Kitchens', 'Bathrooms', 'Tile & patterns', 'Cabinetry & wood', 'Painting'],
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
    heroImages: [
      { src: '/services/plumbing-repair-kitchen.webp', alt: 'LODEX handyman repairing kitchen sink plumbing', position: 'center center' },
      { src: '/services/plumbing-repair-tools.webp', alt: 'LODEX handyman working beneath a kitchen sink with plumbing tools', position: 'center center' },
      { src: '/services/handyman-tools.webp', alt: 'LODEX handyman ready with tools for home repairs and maintenance', position: 'center center' },
    ],
    galleryCategories: ['Painting', 'Cabinetry & wood'],
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
    heroImages: [
      { src: '/services/tv-wall-installation.webp', alt: 'LODEX installer mounting and positioning a television', position: 'center center' },
      { src: '/services/tv-soundbar-installation.webp', alt: 'LODEX installer fitting a soundbar beneath a wall-mounted television', position: 'center center' },
    ],
    galleryCategories: ['Installation'],
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
    heroImages: [
      { src: '/services/materials-procurement.webp', alt: 'LODEX professional organizing fixtures, hardware, finishes, and project materials', position: 'center center' },
    ],
    galleryCategories: ['Materials & surfaces', 'Fabrication'],
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
    heroImages: [
      { src: '/services/pressure-washing-wide.webp', alt: 'LODEX professional pressure washing a residential driveway', position: 'center top' },
      { src: '/services/pressure-washing-entry.webp', alt: 'LODEX professional pressure washing a walkway at a residential entrance', position: 'center top' },
    ],
    galleryCategories: [],
  },
  {
    slug: 'turnkey-rental-launch',
    nav: 'Launch a property',
    title: 'Turnkey Rental / Property Launch',
    short: 'Turnkey property launch',
    summary: 'Renovation, appliances, furnishings, delivery, setup, cleaning, punch list, and rent-ready handoff through one coordinated scope.',
    intro: 'Choose a coordinated Essential, Premium, or White Glove / Signature starting point. Starting budgets are around $25,000, $35,000, and $50,000—not fixed-price guarantees. Final pricing depends on condition, size, scope, selections, location, and licensed-trade requirements.',
    includes: ['Renovation, repair, and final punch list', 'Appliances, furniture, delivery, and installation', 'Wi-Fi/networking, smart locks, cleaning, and setup', 'Rent-ready handoff with one coordinated plan'],
    useCases: ['Essential — starting around $25,000', 'Premium — starting around $35,000', 'White Glove / Signature — starting around $50,000'],
    starter: 'I need a turnkey rental or property launch. The property, current condition, and desired handoff are: ',
    heroImages: [{ src: '/services/renovation-project-planning.webp', alt: 'LODEX turnkey property launch planning and finish selection', position: 'center center' }],
    galleryCategories: ['Kitchens', 'Bathrooms', 'Installation'],
  },
  {
    slug: 'inspection-ready',
    nav: 'Prepare for inspection',
    title: 'Voucher / Section 8 / HCV Inspection-Ready',
    short: 'Inspection-ready support',
    summary: 'Pre-inspection walkthrough, punch list, remediation support, cleanup, photo documentation, and inspection preparation.',
    intro: 'We help owners prepare a property for inspection with practical walkthrough and remediation support. LODEX does not certify or approve Section 8 or HCV compliance.',
    includes: ['Smoke/CO detectors and safety issue punch lists', 'Doors, windows, locks, paint, and patching', 'Appliance checks, cleanup, and repair coordination', 'Photo documentation and inspection preparation'],
    useCases: ['Voucher or HCV inspection preparation', 'Repair and remediation before a scheduled inspection', 'Inspection-ready documentation and final punch list'],
    starter: 'I need inspection-ready or HCV remediation support. The property and known punch-list items are: ',
    heroImages: [{ src: '/services/handyman-tools.webp', alt: 'LODEX inspection-ready repair and remediation support', position: 'center center' }],
    galleryCategories: ['Painting', 'Installation'],
  },
  {
    slug: 'corporate-housing',
    nav: 'House a team',
    title: 'LODEX Corporate Housing',
    short: 'Corporate housing',
    summary: 'Acquire it. Renovate it. Furnish it. House your team.',
    intro: 'For houses purchased or leased by companies for employees: renovation, durable finishes, furnishings, appliances, Wi-Fi, access control, recurring cleaning, maintenance, crew turnover, and property operations.',
    includes: ['Renovation and durable finish programs', 'Beds, desks, TVs, appliances, and furnishings', 'Wi-Fi/networking, access control, and smart locks', 'Recurring cleaning, maintenance, and crew turnover'],
    useCases: ['Workforce and project housing', 'Corporate employee homes', 'Repeat property setup and operations'],
    starter: 'I need LODEX Corporate Housing support. The number of properties, locations, timing, and team needs are: ',
    heroImages: [{ src: '/services/materials-procurement.webp', alt: 'LODEX corporate housing furnishings and durable materials planning', position: 'center center' }],
    galleryCategories: ['Commercial', 'Installation', 'Materials & surfaces'],
  },
]

const legalPages = {
  '/privacy': {
    eyebrow: 'Your information',
    title: 'Privacy Policy',
    intro: 'This policy explains what LODEX collects through this website, how we use it, and the choices available to you.',
    effective: 'Effective August 12, 2026',
    sections: [
      {
        title: 'Information we collect',
        paragraphs: ['We collect information you choose to provide when describing a project, using the intake chat, uploading media, requesting a visit, opening a project record, starting a virtual visit, or making a requested deposit.'],
        bullets: ['Project descriptions, service selections, chat messages, scope confirmations, and related notes.', 'Photos, videos, filenames, descriptions, and automated analysis associated with an upload.', 'Name, phone number, optional email address, job address, preferred date and arrival window.', 'Project code, phone number used for project lookup, project status, and payment status.', 'An anonymous per-tab visitor identifier, the page being viewed, and recent activity time so LODEX can see a live visitor count and respond to support-call requests. The application does not add an IP address to that visitor-presence record.', 'Standard technical records that may be created separately by our hosting systems, such as IP address, browser type, request time, and error or security logs.'],
      },
      {
        title: 'Browser storage and device permissions',
        paragraphs: ['The site uses limited browser storage to remember slideshow position, installation-prompt choices, temporary payment-return context, and a random per-tab visitor identifier. We do not currently use this site to run targeted advertising cookies.', 'Camera and microphone access begins only after you choose to start a virtual visit and your browser grants permission. LODEX does not use the website code to record those streams. Your browser and device settings control permission access.', 'The owner dashboard may provide an audible chime or browser notification for a new visitor, project request, or live-support request after the owner enables notifications. Customer browsing details are not displayed publicly.'],
      },
      {
        title: 'How we use information',
        bullets: ['Understand and respond to project requests.', 'Ask relevant scope questions and prepare for a meet-and-greet or site visit.', 'Analyze customer-provided media and organize project records.', 'Communicate about scheduling, materials, work, payments, and next steps.', 'Operate, secure, troubleshoot, and improve the website and services.', 'Comply with legal obligations and protect customers, LODEX, and others.'],
      },
      {
        title: 'AI-assisted intake',
        paragraphs: ['LODEX may use configured artificial-intelligence service providers to help analyze project descriptions, chat messages, photos, or representative video frames. Automated output is used to support intake and scope review; it is not a final estimate, professional inspection, or promise that a particular repair or method is appropriate. A person should confirm material decisions and final scope.'],
      },
      {
        title: 'How information may be shared',
        paragraphs: ['We may share information only as reasonably needed with hosting, storage, AI, communications, payment, security, and other vendors that help operate LODEX; with contractors or skilled-trade partners involved in evaluating or performing your requested work; when required by law or needed to protect rights and safety; or in connection with a business reorganization or transfer. LODEX does not sell personal information for money.'],
      },
      {
        title: 'Payments',
        paragraphs: ['Requested deposits are handled through Stripe-hosted Checkout. Payment-card details are submitted to Stripe rather than entered into the LODEX website. LODEX may receive transaction identifiers, status, amount, customer email, and related payment records needed to match a deposit to a project. Stripe handles payment data under its own terms and privacy policy.'],
      },
      {
        title: 'Retention and security',
        paragraphs: ['We retain project and contact information for as long as reasonably needed to respond, perform or document services, handle accounting or disputes, meet legal obligations, and maintain legitimate business records. Retention may vary by record type and project status.', 'We use reasonable administrative and technical safeguards appropriate to the information we maintain. No website, transmission, or storage system can be guaranteed completely secure.'],
      },
      {
        title: 'Your choices',
        paragraphs: ['You may ask to review, correct, or delete information you provided by calling LODEX. We may need to verify your identity and may retain information when required by law, needed for an active project, payment or dispute, or permitted for legitimate business purposes. You can block browser storage or withdraw camera and microphone permission through your browser settings, although some features may stop working.'],
      },
      {
        title: 'Children and policy changes',
        paragraphs: ['The site is intended for adults arranging property-related services and is not directed to children under 13. We may update this policy as the site or our practices change. The effective date above identifies the current version.'],
      },
    ],
  },
  '/terms': {
    eyebrow: 'Using LODEX',
    title: 'Terms & Conditions',
    intro: 'These terms govern use of the LODEX website. A separate written quote, work order, or agreement will control the actual services for a project.',
    effective: 'Effective August 12, 2026',
    sections: [
      {
        title: 'Website use and acceptance',
        paragraphs: ['By using this website, submitting a request, or uploading content, you agree to these terms and the Privacy Policy. If you do not agree, do not submit information through the site. You must be at least 18 and able to enter a binding agreement.'],
      },
      {
        title: 'Requests are not final quotes or contracts',
        paragraphs: ['Website descriptions, chat responses, automated analysis, scheduling requests, project records, inspiration images, and preliminary discussions are informational. They do not create a contract, guarantee availability, or establish a final price, schedule, scope, code determination, or repair method. Actual work begins only after LODEX and the customer confirm the applicable scope and terms, normally in a written quote, work order, or project agreement.'],
      },
      {
        title: 'Services, trades, and permits',
        paragraphs: ['Service availability depends on the project, location, site conditions, materials, staffing, and any licensing or permit requirements. Work requiring a separately licensed trade or permit may be referred to or coordinated with an appropriately qualified provider and addressed in the project-specific agreement. LODEX may decline work that is unsafe, outside scope, unlawful, or not a practical fit.'],
      },
      {
        title: 'Customer responsibilities',
        bullets: ['Provide accurate information about the property, desired outcome, access, dimensions, utilities, known hazards, and prior work.', 'Confirm that you own the property or are authorized to request and approve the work.', 'Provide safe and timely access and keep children, pets, valuables, and unauthorized persons away from the work area.', 'Do not conceal hazardous materials, structural concerns, active leaks, unsafe electrical conditions, or other material risks.', 'Review and approve the final scope, materials, pricing, and project-specific terms before work begins.'],
      },
      {
        title: 'Materials, sourcing, and installation',
        paragraphs: ['Customer approval may be required before LODEX purchases or orders materials. Product availability, color, dimensions, lead times, manufacturer changes, delivery damage, return windows, restocking charges, and warranties are controlled in part by suppliers and manufacturers. Project-specific documents will identify material allowances, ownership, reimbursement, returns, and installation responsibilities when applicable.'],
      },
      {
        title: 'Scheduling, deposits, and payments',
        paragraphs: ['A requested appointment is not confirmed until LODEX accepts it. Arrival windows and completion dates may change because of traffic, weather, site conditions, supplier delays, emergencies, or scope changes.', 'Pay a deposit only through a LODEX request linked to your project. Deposit amount, application, refundability, cancellation treatment, progress payments, and final balance are governed by the applicable quote or project agreement. Stripe may apply its own terms to payment processing.'],
      },
      {
        title: 'Uploads, AI tools, and virtual visits',
        paragraphs: ['You keep ownership of content you submit. You grant LODEX permission to store, copy, analyze, and share it only as reasonably needed to evaluate, coordinate, document, and perform the requested services. Do not upload content you lack permission to share or content containing unnecessary sensitive information.', 'AI-assisted intake can be incomplete or wrong and must not be treated as a final estimate, diagnosis, engineering conclusion, safety instruction, or substitute for an appropriate in-person review. During a virtual visit, do not climb, open energized equipment, move dangerous objects, or take any action that could put you or others at risk.'],
      },
      {
        title: 'Inspiration and intellectual property',
        paragraphs: ['The inspiration archive includes AI-generated concepts and is not a representation that LODEX completed the depicted work. Feasibility, materials, price, and outcome depend on the real property and confirmed scope.', 'The LODEX name, logos, site design, copy, and site-owned media are protected by applicable intellectual-property laws. You may use the website for personal project evaluation, but may not copy, republish, scrape, sell, or create misleading uses of site content without permission.'],
      },
      {
        title: 'Website availability and responsibility',
        paragraphs: ['The website is provided on an as-available basis and may contain errors or interruptions. To the extent permitted by law, LODEX is not responsible for indirect or consequential loss caused solely by use of, or inability to use, the website. Any warranties, remedies, limits, or responsibilities for actual services will be stated in the project-specific agreement. Nothing in these terms waives rights or responsibilities that cannot lawfully be waived.'],
      },
      {
        title: 'Ohio law, updates, and contact',
        paragraphs: ['These website terms are governed by Ohio law, without limiting consumer protections that apply by law. We may update these terms as the website or services change; the effective date identifies the current version. Questions can be directed to LODEX by phone.'],
      },
    ],
  },
}

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

function asGallerySlide(project) {
  return { id: project.id, type: 'image', src: project.src, alt: project.alt, title: project.title, eyebrow: project.category, position: 'center center' }
}

function asServiceSlide(service, image, index) {
  return { id: `${service.slug}-${index}`, type: 'image', ...image, title: service.title, eyebrow: service.short }
}

function rotateFromStoredPosition(items, storageKey, step = 1) {
  if (!items.length) return []
  let start = 0
  try {
    const stored = Number.parseInt(window.localStorage.getItem(storageKey) || '', 10)
    if (Number.isInteger(stored)) start = ((stored % items.length) + items.length) % items.length
    window.localStorage.setItem(storageKey, String((start + step) % items.length))
  } catch {}
  return [...items.slice(start), ...items.slice(0, start)]
}

const brandedHeroSlides = services.flatMap(service => service.heroImages.map((image, index) => asServiceSlide(service, image, index)))
const galleryHeroSlides = lzGalleryProjects
  .filter(project => ['Kitchens', 'Bathrooms', 'Commercial', 'Installation', 'Painting', 'Tile & patterns'].includes(project.category))
  .map(asGallerySlide)
const homePhotoSlides = rotateFromStoredPosition([...brandedHeroSlides, ...galleryHeroSlides], 'lodex-home-reel-start', 7).slice(0, 7)
const brandLogoSlide = sequence => ({ id: `lodex-logo-${sequence}`, type: 'image', brand: true, src: '/lodex-logo-home-business.webp', alt: 'LODEX Home & Business Services', position: 'center center', title: 'Home · Business · Enterprise', eyebrow: 'One LODEX service family' })
const homeHeroSlides = [
  ...homePhotoSlides.slice(0, 2),
  brandLogoSlide(1),
  ...homePhotoSlides.slice(2, 5),
  brandLogoSlide(2),
  ...homePhotoSlides.slice(5, 7),
  brandLogoSlide(3),
]

const messages = ref([{ role: 'assistant', text: 'What can LODEX take off your plate? Choose a service below, tell us in your own words, or show us the space.' }])
const activeService = computed(() => services.find(service => currentPath.value.replace(/\/$/, '') === `/services/${service.slug}`) || null)
const isInspirationPage = computed(() => currentPath.value.replace(/\/$/, '') === '/inspiration')
const isAdminPage = computed(() => currentPath.value.replace(/\/$/, '') === '/admin')
const activeLegalPage = computed(() => legalPages[currentPath.value.replace(/\/$/, '')] || null)
const isHomePage = computed(() => !activeService.value && !isInspirationPage.value && !isAdminPage.value && !activeLegalPage.value)
const homeHeroSlide = computed(() => homeHeroSlides[homeHeroSlideIndex.value] || homeHeroSlides[0])
const activeHeroImage = computed(() => serviceHeroSlides.value[serviceHeroSlideIndex.value] || null)
const availableGalleryProjects = computed(() => lzGalleryProjects.filter(project => !hiddenGallerySources.value.has(project.src)))
const inspirationProjects = computed(() => availableGalleryProjects.value.slice(0, 12))
const galleryCategories = computed(() => ['All', ...new Set(availableGalleryProjects.value.map(project => project.category))])
const filteredGalleryProjects = computed(() => galleryFilter.value === 'All' ? availableGalleryProjects.value : availableGalleryProjects.value.filter(project => project.category === galleryFilter.value))
const visibleGalleryProjects = computed(() => filteredGalleryProjects.value.slice(0, galleryVisible.value))
const lightboxCollection = computed(() => isInspirationPage.value ? filteredGalleryProjects.value : inspirationProjects.value)
const summary = computed(() => messages.value.filter(item => item.role === 'user').map(item => item.text).join('\n'))
const hasCustomerMessage = computed(() => messages.value.some(item => item.role === 'user'))
const scopePercent = computed(() => agreed.value ? 100 : qualification.value.progress || 0)
const scopeLabel = computed(() => agreed.value ? 'Scope confirmed' : intakeReady.value ? 'Ready for the next step' : qualification.value.qualified ? 'Lead qualified · optional details' : hasCustomerMessage.value ? 'Qualifying the project' : 'Ready when you are')
const canSchedule = computed(() => hasCustomerMessage.value || uploaded.value)
const intakeTitle = computed(() => selectedService.value?.title || 'Your project')
const segmentTitle = computed(() => SEGMENT_LABELS[customerSegment.value] || 'Choose your LODEX team')

function formatFee(cents) {
  if (!Number.isInteger(cents) || cents <= 0) return ''
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100)
}

function pricingMessage(record) {
  if (!record) return ''
  const amount = formatFee(record.visit_fee_cents)
  if (amount) return `${record.visit_fee_label || 'Project Assessment'} — ${amount}`
  if (record.customer_segment === 'enterprise') return 'Custom Assessment — We’ll review the scope and confirm the appropriate visit/project setup.'
  return 'Assessment amount pending — We’ll confirm route distance and the combined visit amount.'
}

function paymentAvailable(record) {
  if (!record) return false
  if (record.customer_segment) return Number.isInteger(record.visit_fee_cents) && record.visit_fee_cents > 0
  return true
}

function onSegmentChanged(event) {
  customerSegment.value = event.detail?.segment || readStoredSegment()
  homeProjectSize.value = event.detail?.projectSizeClass || readStoredHomeProjectSize()
}

function preloadSlide(slide) {
  if (!slide || slide.type !== 'image') return
  const image = new Image()
  image.src = slide.src
}

function advanceHomeHero() {
  if (!homeHeroSlides.length) return
  homeHeroSlideIndex.value = (homeHeroSlideIndex.value + 1) % homeHeroSlides.length
}

function advanceServiceHero() {
  if (!serviceHeroSlides.value.length) return
  serviceHeroSlideIndex.value = (serviceHeroSlideIndex.value + 1) % serviceHeroSlides.value.length
}

function scheduleHomeHero() {
  window.clearTimeout(homeReelTimer)
  if (!isHomePage.value || homeReelPaused.value || homeHeroSlide.value?.type === 'video') return
  const nextSlide = homeHeroSlides[(homeHeroSlideIndex.value + 1) % homeHeroSlides.length]
  preloadSlide(nextSlide)
  homeReelTimer = window.setTimeout(advanceHomeHero, 4800)
}

function scheduleServiceHero() {
  window.clearTimeout(serviceReelTimer)
  if (!activeService.value || serviceReelPaused.value || serviceHeroSlides.value.length < 2) return
  const nextSlide = serviceHeroSlides.value[(serviceHeroSlideIndex.value + 1) % serviceHeroSlides.value.length]
  preloadSlide(nextSlide)
  serviceReelTimer = window.setTimeout(advanceServiceHero, 5600)
}

function toggleHomeReel() {
  homeReelPaused.value = !homeReelPaused.value
  nextTick(() => {
    if (!homeVideoRef.value) return
    if (homeReelPaused.value) homeVideoRef.value.pause()
    else homeVideoRef.value.play().catch(() => {})
  })
}

function toggleServiceReel() { serviceReelPaused.value = !serviceReelPaused.value }

watch(activeService, service => {
  window.clearTimeout(serviceReelTimer)
  serviceHeroSlideIndex.value = 0
  serviceReelPaused.value = prefersReducedMotion
  if (!service) {
    serviceHeroSlides.value = []
    return
  }
  const branded = service.heroImages.map((image, index) => asServiceSlide(service, image, index))
  const related = availableGalleryProjects.value.filter(project => service.galleryCategories.includes(project.category)).map(asGallerySlide)
  serviceHeroSlides.value = rotateFromStoredPosition([...branded, ...related], `lodex-service-reel-${service.slug}`)
}, { immediate: true })

watch([homeHeroSlide, homeReelPaused, isHomePage], scheduleHomeHero, { immediate: true })
watch([activeHeroImage, serviceReelPaused], scheduleServiceHero, { immediate: true })
watch(isInspirationPage, () => nextTick(observeGallerySentinel), { immediate: true })

function serviceHref(service) { return `/services/${service.slug}` }
function openInspiration(project) { selectedInspiration.value = project }
function openInspirationGallery() { navigate('/inspiration') }
function hideGalleryImage(project) {
  const next = new Set(hiddenGallerySources.value)
  next.add(project.src)
  hiddenGallerySources.value = next
}
function loadMoreGallery() {
  if (galleryLoading.value || visibleGalleryProjects.value.length >= filteredGalleryProjects.value.length) return
  galleryLoading.value = true
  galleryVisible.value = Math.min(galleryVisible.value + 24, filteredGalleryProjects.value.length)
  nextTick(() => { galleryLoading.value = false; observeGallerySentinel() })
}
function observeGallerySentinel() {
  galleryObserver?.disconnect()
  galleryObserver = null
  if (!isInspirationPage.value || !gallerySentinel.value || !('IntersectionObserver' in window)) return
  galleryObserver = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) loadMoreGallery()
  }, { rootMargin: '700px 0px' })
  galleryObserver.observe(gallerySentinel.value)
}
function selectGalleryFilter(category) {
  galleryFilter.value = category
  galleryVisible.value = 24
  nextTick(observeGallerySentinel)
}
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
async function fetchWithTimeout(resource, options = {}, timeoutMs = 25000) {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(resource, { ...options, signal: controller.signal })
  } catch (error) {
    if (error?.name === 'AbortError') throw new Error('The service took too long to respond. Please try again.')
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}
async function upload() {
  if (!selectedFile.value || uploadSending.value) return
  const form = new FormData()
  form.append('file', selectedFile.value)
  form.append('description', description.value)
  form.append('service_category', selectedService.value?.title || '')
  uploadSending.value = true
  try {
    const response = await fetchWithTimeout('/api/intake/upload', { method: 'POST', body: form }, 60000)
    const data = await readApiResponse(response, 'Upload failed.')
    uploaded.value = data
    add('assistant', `I received ${data.filename}.\n\n${data.analysis}`)
  } catch (error) { add('assistant', error.message) } finally { uploadSending.value = false }
}
async function send() {
  const text = message.value.trim()
  if (!text || chatSending.value) return
  message.value = ''
  add('user', text)
  chatSending.value = true
  try {
    const conversation = serializeConversation(messages.value)
    const response = await fetchWithTimeout('/api/intake/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, project_summary: summary.value, media_notes: uploaded.value ? `${uploaded.value.filename}: ${description.value}` : '', service_category: selectedService.value?.title || '', conversation }) })
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
  } catch (error) { add('assistant', `${error.message} We can still collect the details and arrange a meet-and-greet.`) } finally { chatSending.value = false }
}
async function book() {
  sending.value = true
  notice.value = ''
  paymentStatus.value = 'not_started'
  paymentError.value = ''
  try {
    const uploads = uploaded.value ? [{ upload_id: uploaded.value.upload_id, filename: uploaded.value.filename, media_type: uploaded.value.media_type, description: description.value }] : []
    const conversation = serializeConversation(messages.value)
    const response = await fetch('/api/appointments/request', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...appointment.value, project_summary: summary.value || 'Customer requested an in-person meet-and-greet.', service_category: selectedService.value?.title || 'General inquiry', uploads, conversation, assumptions_confirmed: agreed.value, intake_ready: qualification.value.qualified }) })
    const data = await readApiResponse(response, 'Could not request appointment.')
    notice.value = data.message
    projectCode.value = data.project_code || ''
    projectPhone.value = appointment.value.phone
    confirmation.value = data.confirmation || { ...appointment.value, project_summary: summary.value, service_category: selectedService.value?.title || 'General inquiry', uploads }
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
async function openVirtualMeet(roomCode = '') {
  const requestedRoom = typeof roomCode === 'string' ? roomCode : ''
  virtualRoom.value = String(requestedRoom || projectCode.value || project.value?.project_code || `LDX-${Math.random().toString(36).slice(2, 8).toUpperCase()}`).trim().toUpperCase()
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
function ensureVisitorId() {
  try {
    visitorId.value = sessionStorage.getItem('lodex-visitor-id') || ''
    if (!visitorId.value) {
      visitorId.value = `lv_${crypto.randomUUID().replaceAll('-', '')}`
      sessionStorage.setItem('lodex-visitor-id', visitorId.value)
    }
  } catch {
    visitorId.value = `lv_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`
  }
}
async function sendPresence() {
  if (isAdminPage.value || !visitorId.value) return
  try {
    await fetch('/api/presence/heartbeat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ visitor_id: visitorId.value, path: `${window.location.pathname}${window.location.hash}`, page_title: document.title }) })
  } catch {}
}
async function requestSupportCall() {
  supportStatus.value = 'Alerting LODEX…'
  try {
    const response = await fetch('/api/support/call', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ visitor_id: visitorId.value, name: supportRequest.value.name || appointment.value.name, phone: supportRequest.value.phone || appointment.value.phone, project_code: projectCode.value, message: supportRequest.value.message }) })
    const data = await readApiResponse(response, 'Could not request live support.')
    supportStatus.value = data.message
    supportOpen.value = false
    await openVirtualMeet(data.room_code)
  } catch (supportError) { supportStatus.value = supportError.message }
}
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
function onPopState() { currentPath.value = window.location.pathname; sendPresence() }
onMounted(() => { window.addEventListener('popstate', onPopState); window.addEventListener('keydown', onKeydown); window.addEventListener('lodex:segment-changed', onSegmentChanged); ensureVisitorId(); sendPresence(); presenceTimer = window.setInterval(sendPresence, 25000); handlePaymentReturn(); nextTick(observeGallerySentinel) })
onBeforeUnmount(() => { window.removeEventListener('popstate', onPopState); window.removeEventListener('keydown', onKeydown); window.removeEventListener('lodex:segment-changed', onSegmentChanged); window.clearTimeout(homeReelTimer); window.clearTimeout(serviceReelTimer); galleryObserver?.disconnect(); window.clearInterval(presenceTimer); stopVirtualMedia() })
</script>

<template>
  <main>
    <div v-if="!isAdminPage" class="utility-bar"><span>Northeast Ohio · Residential & commercial</span><a :href="phoneHref">Call LODEX · {{ phone }}</a></div>
    <nav v-if="!isAdminPage" class="site-nav" aria-label="Primary navigation">
      <a class="brand" href="/" @click.prevent="goHome" aria-label="LODEX home"><img class="brand-logo" src="/lodex-logo-home-business.webp" alt="LODEX Home & Business Services" /></a>
      <div class="nav-links"><a href="/#services" @click.prevent="goHome('#services')">Services</a><a href="/inspiration" @click.prevent="openInspirationGallery">Inspiration</a><a href="/#how-it-works" @click.prevent="goHome('#how-it-works')">How it works</a><a href="/#project" @click.prevent="goHome('#project')">My project</a></div>
      <button type="button" class="nav-cta" @click="goHome(); nextTick(openSchedule)">Start a project <span>↗</span></button>
    </nav>

    <AdminPanel v-if="isAdminPage" @join-room="openVirtualMeet" />

    <template v-else-if="activeService">
      <section class="service-hero page-width">
        <a class="back-link" href="/" @click.prevent="goHome">← All services</a>
        <p class="eyebrow">LODEX services / {{ activeService.short }}</p>
        <div class="service-hero-grid">
          <div><h1>{{ activeService.title }}</h1><p class="service-lede">{{ activeService.intro }}</p><div class="hero-actions"><button type="button" class="primary-button" @click="startFromService(activeService)">Start this project <span>↗</span></button><a class="phone-link" :href="phoneHref">Call {{ phone }}</a></div></div>
          <div v-if="activeHeroImage" class="service-hero-media">
            <Transition name="reel-fade">
              <img :key="activeHeroImage.id" class="service-reel-image" :src="activeHeroImage.src" :alt="activeHeroImage.alt" :style="{ objectPosition: activeHeroImage.position }" width="1254" height="1254" fetchpriority="high" decoding="async" @error="advanceServiceHero" />
            </Transition>
            <button v-if="serviceHeroSlides.length > 1" type="button" class="reel-toggle service-reel-toggle" :aria-label="serviceReelPaused ? 'Play service slideshow' : 'Pause service slideshow'" @click="toggleServiceReel">{{ serviceReelPaused ? '▶' : 'Ⅱ' }}</button>
            <span v-if="serviceHeroSlides.length > 1" class="service-reel-count">{{ serviceHeroSlideIndex + 1 }} / {{ serviceHeroSlides.length }}</span>
            <aside class="service-callout"><span>What we handle</span><b>{{ activeService.summary }}</b><small>Tell us the outcome you want. We’ll confirm the right scope before any final price is set.</small></aside>
          </div>
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
          <button v-for="category in galleryCategories" :key="category" type="button" :class="{ active: galleryFilter === category }" @click="selectGalleryFilter(category)">{{ category }}<span>{{ category === 'All' ? availableGalleryProjects.length : availableGalleryProjects.filter(project => project.category === category).length }}</span></button>
        </div>
        <p class="gallery-status">Showing {{ visibleGalleryProjects.length }} of {{ filteredGalleryProjects.length }} concepts</p>
        <div class="archive-grid">
          <figure v-for="project in visibleGalleryProjects" :key="project.id" tabindex="0" role="button" :aria-label="`View ${project.title}`" @click="openInspiration(project)" @keydown.enter="openInspiration(project)" @keydown.space.prevent="openInspiration(project)">
            <img :src="project.src" :alt="project.alt" loading="lazy" decoding="async" @error="hideGalleryImage(project)"/>
            <figcaption><span>{{ project.category }}</span><b>{{ project.title }}</b></figcaption>
          </figure>
        </div>
        <div ref="gallerySentinel" class="gallery-sentinel" aria-hidden="true"></div>
        <p v-if="galleryLoading" class="gallery-loading">Loading more concepts…</p>
      </section>
      <section class="gallery-cta"><div class="page-width"><p class="eyebrow">Turn inspiration into a real scope</p><h2>Show us the idea and the space you actually have.</h2><button type="button" class="primary-button" @click="goHome('#intake')">Start your project <span>↗</span></button></div></section>
    </template>

    <template v-else-if="activeLegalPage">
      <article class="legal-page page-width">
        <a class="back-link" href="/" @click.prevent="goHome">← LODEX home</a>
        <header class="legal-hero"><p class="eyebrow">{{ activeLegalPage.eyebrow }}</p><h1>{{ activeLegalPage.title }}</h1><p>{{ activeLegalPage.intro }}</p><small>{{ activeLegalPage.effective }}</small></header>
        <div class="legal-layout">
          <aside><a v-for="(section, index) in activeLegalPage.sections" :key="section.title" :href="`#legal-${index}`">{{ section.title }}</a></aside>
          <div class="legal-content"><section v-for="(section, index) in activeLegalPage.sections" :id="`legal-${index}`" :key="section.title"><h2>{{ section.title }}</h2><p v-for="paragraph in section.paragraphs || []" :key="paragraph">{{ paragraph }}</p><ul v-if="section.bullets"><li v-for="bullet in section.bullets" :key="bullet">{{ bullet }}</li></ul></section><section class="legal-contact"><h2>Contact LODEX</h2><p>Questions about these terms or your information can be directed to <a :href="phoneHref">{{ phone }}</a>.</p></section></div>
        </div>
      </article>
    </template>

    <template v-else>
      <section id="top" class="hero page-width">
        <div class="hero-copy"><p class="eyebrow">LODEX · Northeast Ohio</p><h1>One call. <em>Real progress.</em></h1><p class="lede">From repairs and maintenance to delivery, installation, cleanup, restoration, and larger improvements, LODEX gives you one local point of contact and a clear next step.</p><div class="hero-value-points" aria-label="Why start with LODEX"><span>One point of contact</span><span>Photo-first intake</span><span>Residential & commercial</span></div><div class="hero-service-lanes" aria-label="Choose a LODEX service"><button v-for="service in services" :key="service.slug" type="button" @click="chooseService(service); scrollToIntake()">{{ service.nav }}</button></div><div class="hero-actions"><button type="button" class="primary-button" @click="scrollToIntake">Start with your project <span>↗</span></button><a class="phone-link" :href="phoneHref">Or call {{ phone }}</a></div></div>
        <div class="hero-visual" aria-label="LODEX services and project inspiration slideshow">
          <Transition name="reel-fade">
            <img v-if="homeHeroSlide.type === 'image'" :key="homeHeroSlide.id" class="hero-reel-media" :class="{ 'brand-logo-slide': homeHeroSlide.brand }" :src="homeHeroSlide.src" :alt="homeHeroSlide.alt" :style="{ objectPosition: homeHeroSlide.position }" width="1254" height="1254" fetchpriority="high" decoding="async" @error="advanceHomeHero" />
            <video v-else :key="homeHeroSlide.id" ref="homeVideoRef" class="hero-reel-media hero-reel-video" autoplay muted playsinline preload="metadata" :poster="homeHeroSlide.poster" aria-label="Animated LODEX Home Services logo" @ended="advanceHomeHero" @error="advanceHomeHero"><source :src="homeHeroSlide.src" type="video/mp4"/></video>
          </Transition>
          <div class="hero-video-scrim"></div>
          <button type="button" class="reel-toggle home-reel-toggle" :aria-label="homeReelPaused ? 'Play homepage slideshow' : 'Pause homepage slideshow'" @click="toggleHomeReel">{{ homeReelPaused ? '▶' : 'Ⅱ' }}</button>
          <div class="hero-media-caption"><span>{{ homeHeroSlide.eyebrow }}</span><b>{{ homeHeroSlide.title }}</b></div>
          <div class="hero-reel-dots" aria-hidden="true"><i v-for="(_, index) in homeHeroSlides" :key="index" :class="{ active: index === homeHeroSlideIndex }"></i></div>
        </div>
      </section>

      <section id="inspiration" class="inspiration-section page-width"><div class="section-heading"><div><p class="eyebrow">LZ Custom inspiration · {{ availableGalleryProjects.length }} concepts</p><h2>See what thoughtful work can look like.</h2></div><div class="inspiration-intro"><button type="button" class="text-button" @click="openInspirationGallery">Explore all {{ availableGalleryProjects.length }} concepts →</button></div></div><div class="inspiration-grid"><figure v-for="project in inspirationProjects" :key="project.src" tabindex="0" role="button" :aria-label="`View ${project.title}`" @click="openInspiration(project)" @keydown.enter="openInspiration(project)" @keydown.space.prevent="openInspiration(project)"><img :src="project.src" :alt="project.title" loading="lazy" @error="hideGalleryImage(project)"/><figcaption><b>{{ project.title }}</b><span>{{ project.detail }}</span></figcaption></figure></div><button type="button" class="gallery-more gallery-more-home" @click="openInspirationGallery">Open the complete inspiration archive <span>↗</span></button></section>

      <section id="services" class="services-section page-width"><div class="section-heading"><div><p class="eyebrow">LODEX services</p><h2>Renovate, repair, deliver, source, and restore.</h2></div><p>Five clear ways to start. Every service begins with a practical look at scope, access, timing, materials, and the next step.</p></div><div class="service-grid"><a v-for="(service, index) in services" :key="service.slug" class="service-card" :href="serviceHref(service)" @click.prevent="openService(service)"><span>0{{ index + 1 }}</span><h3>{{ service.title }}</h3><p>{{ service.summary }}</p><b>Explore service →</b></a></div></section>

      <section id="laser-restoration" class="laser-showcase"><div class="page-width"><div class="section-heading"><div><p class="eyebrow">LODEX × Cyber Carp</p><h2>Laser restoration you can see.</h2></div><p>Rust, paint, surface buildup, and fire residue—shown in real working clips, not stock footage.</p></div><div class="laser-grid"><article v-for="project in laserProjects" :key="project.video" class="laser-card"><video :autoplay="project.featured" muted loop playsinline controls preload="metadata" :poster="project.poster" :aria-label="project.title"><source :src="project.video" type="video/mp4"/></video><div><span>{{ project.category }}</span><h3>{{ project.title }}</h3><p>{{ project.description }}</p></div></article></div><div class="laser-showcase-actions"><button type="button" class="primary-button" @click="openService(services[4])">Explore cleaning & restoration <span>↗</span></button><button type="button" class="text-button" @click="chooseService(services[4]); scrollToIntake()">Show us your surface →</button></div></div></section>

      <section id="how-it-works" class="how-section"><div class="page-width"><p class="eyebrow">Simple by design</p><div class="how-grid"><h2>Clear scope before the work begins.</h2><div class="how-steps"><div><b>01</b><h3>Tell us the outcome</h3><p>Choose a service, describe the job, or send photos and short video.</p></div><div><b>02</b><h3>Confirm the real details</h3><p>We ask only what is needed to understand scope, access, timing, and materials.</p></div><div><b>03</b><h3>Set the next step</h3><p>Request a meet-and-greet or coordinated visit—then get a clear, confirmed plan.</p></div></div></div></div></section>

      <section id="intake" class="intake-section"><div class="page-width"><div class="intake-head"><div><p class="eyebrow">Start your project</p><h2>Let’s figure out <em>what’s next.</em></h2><p class="intake-copy"><b>{{ segmentTitle }}</b><template v-if="customerSegment === 'home' && homeProjectSize"> · {{ homeProjectSize }} homeowner project</template><br/>Selected service: <b>{{ intakeTitle }}</b></p></div><div class="scope-meter"><div class="scope-meter-top"><span>{{ scopeLabel }}</span><b>{{ scopePercent }}%</b></div><div class="meter-track"><i :style="{ width: `${scopePercent}%` }"></i></div><small>{{ qualification.qualified ? 'The required facts are covered; useful extras can still improve the visit.' : 'Progress reflects the service facts we actually need—not the number of messages.' }}</small></div></div>
        <div class="service-chips" aria-label="Choose a service"><button v-for="service in services" :key="service.slug" type="button" :class="{ selected: selectedService?.slug === service.slug }" @click="chooseService(service, false)">{{ service.short }}</button></div>
        <div class="flow"><span :class="{ active: step === 'chat' }">1. Talk it through</span><span :class="{ active: step === 'schedule' }">2. Request a visit</span><span :class="{ active: step === 'done' }">3. Keep the details</span></div>
        <div v-if="step === 'chat'" class="workspace"><div class="chat-card"><div class="chat-title"><i></i><div><b>LODEX project intake</b><small>Human-friendly questions, with AI help when useful.</small></div><button type="button" class="mini-link" @click="openSchedule">Request a visit ↗</button></div><div class="messages"><article v-for="(item, index) in messages" :key="index" :class="item.role"><p>{{ item.text }}</p></article><div v-if="chatSending" class="assistant"><p class="typing">Thinking through the project…</p></div></div><form class="composer" @submit.prevent="send"><textarea v-model="message" :disabled="chatSending" placeholder="For example: I need a TV mounted above a brick fireplace…" rows="3"></textarea><button type="submit" :disabled="chatSending || !message.trim()">Send</button></form></div>
          <aside class="upload-card"><p class="eyebrow">Helpful, not required</p><h3>Show us the work area.</h3><p>Photos and short videos help us ask better questions. They do not create a final estimate.</p><label class="file-picker"><input type="file" accept="image/jpeg,image/png,image/webp,image/heic,video/mp4,video/quicktime,video/webm" @change="selectedFile = $event.target.files[0]"/><span>{{ selectedFile ? selectedFile.name : 'Choose photo or video' }}</span><b>＋</b></label><textarea v-model="description" placeholder="Anything we should notice?"></textarea><button type="button" class="outline-button" @click="upload" :disabled="!selectedFile || uploadSending">{{ uploadSending ? 'Uploading…' : 'Upload & analyze' }}</button><div v-if="qualification.requirements.length" class="qualification-checklist"><small>{{ qualification.label }}</small><ul><li v-for="item in qualification.requirements" :key="item.id" :class="{ covered: item.covered }"><span>{{ item.covered ? '✓' : '○' }}</span>{{ item.label }}</li></ul></div><label class="confirm"><input v-model="agreed" type="checkbox" :disabled="!hasCustomerMessage"/><span>I reviewed the captured scope and it is accurate to the best of my knowledge.</span></label><button type="button" class="ready-button" @click="openSchedule" :disabled="!canSchedule">{{ qualification.qualified ? 'Choose a visit time' : 'Continue to meet-and-greet' }} <span>↗</span></button></aside></div>
        <form v-else-if="step === 'schedule'" class="schedule-card" @submit.prevent="book"><div><p class="eyebrow">Next: a real-world check</p><h3>Request your meet-and-greet.</h3><p>{{ handoffMessage || 'Choose a preferred window. We’ll confirm the visit and clarify anything still unknown before a final price is set.' }}</p></div><div class="fields"><input v-model="appointment.name" required placeholder="Your name"/><input v-model="appointment.phone" required placeholder="Phone"/><input v-model="appointment.email" type="email" placeholder="Email (optional)"/><input v-model="appointment.address" required placeholder="Job address"/><input v-model="appointment.preferred_date" required type="date"/><select v-model="appointment.preferred_time" required><option disabled value="">Preferred arrival window</option><option>Morning · 9 AM–12 PM</option><option>Afternoon · 12 PM–3 PM</option><option>Late afternoon · 3 PM–6 PM</option></select></div><div class="schedule-actions"><button type="submit" class="primary-button" :disabled="sending">{{ sending ? 'Sending…' : 'Request meet-and-greet' }} <span>↗</span></button><button type="button" class="back-button" @click="step = 'chat'">Back to conversation</button></div><p v-if="notice" class="notice">{{ notice }}</p></form>
        <div v-else class="success-card"><img class="confirmation-logo" src="/lodex-logo-home-business.webp" alt="LODEX Home & Business Services"/><p class="eyebrow">Request received</p><h3>Everything we received is shown below.</h3><p>{{ notice }}</p><div v-if="projectCode" class="project-code"><span>Your project code</span><b>{{ projectCode }}</b><small>Save this code with the phone number you used. You can return to the project portal below.</small></div><div v-if="confirmation" class="assessment-summary"><b>{{ pricingMessage(confirmation) }}</b><small v-if="confirmation.visit_fee_cents">Your visit price reflects project type and route distance. The amount shown is calculated by LODEX on the server.</small><small v-else>We never invent mileage. LODEX will review the address and confirm the amount before payment.</small></div><div v-if="confirmation" class="confirmation-details"><div><span>Division</span><b>{{ SEGMENT_LABELS[confirmation.customer_segment] || 'LODEX' }}</b></div><div><span>Service</span><b>{{ confirmation.service_category }}</b></div><div><span>Preferred visit</span><b>{{ confirmation.preferred_date }} · {{ confirmation.preferred_time }}</b></div><div><span>Job address</span><b>{{ confirmation.address }}</b></div><div><span>Contact</span><b>{{ confirmation.name }} · {{ confirmation.phone }}<template v-if="confirmation.email"> · {{ confirmation.email }}</template></b></div><section><span>Project details</span><p>{{ confirmation.project_summary }}</p></section><section><span>Attachments</span><p v-if="confirmation.uploads?.length">{{ confirmation.uploads.map(file => file.filename).join(', ') }}</p><p v-else>No files attached.</p></section></div><div class="confirmation-actions"><button type="button" class="virtual-button" @click="openVirtualMeet">▣ Start a virtual meet-and-greet</button><div v-if="paymentStatus === 'paid'" class="payment-confirmed">Assessment payment recorded.</div><button v-else-if="paymentAvailable(confirmation)" type="button" class="primary-button" @click="startDeposit" :disabled="sending">{{ sending ? 'Opening secure checkout…' : `Pay ${confirmation.visit_fee_label || 'assessment'}` }} <span>↗</span></button></div><p v-if="paymentError" class="error">{{ paymentError }}</p><a class="text-link" href="#project">Open my project details →</a></div>
      </div></section>

      <section id="project" class="project-section page-width"><div class="section-heading"><div><p class="eyebrow">Returning customers</p><h2>Your project, in one place.</h2></div><p>Use your project code and the phone number on the request to see the latest scope and next step.</p></div><form class="lookup-card" @submit.prevent="lookupProject"><label>Project code<input v-model="projectCode" placeholder="LDX-123456" autocomplete="off"/></label><label>Phone used for the request<input v-model="projectPhone" type="tel" placeholder="216-555-0123" autocomplete="tel"/></label><button type="submit" class="primary-button">Open my project <span>↗</span></button><p v-if="projectError" class="error">{{ projectError }}</p><div v-if="project" class="project-result"><img class="confirmation-logo" src="/lodex-logo-home-business.webp" alt="LODEX Home & Business Services"/><div class="project-result-top"><span>{{ project.status }}</span><b>{{ project.progress }}%</b></div><h3>{{ project.title }}</h3><p v-if="project.service_category" class="project-service">{{ project.service_category }}</p><p>{{ project.next_step }}</p><div class="assessment-summary"><b>{{ pricingMessage(project) }}</b><small v-if="project.visit_fee_cents">One combined amount; project type and route distance are already reflected.</small><small v-else-if="project.customer_segment">LODEX will confirm the appropriate setup before payment.</small></div><div class="meter-track"><i :style="{ width: `${project.progress}%` }"></i></div><small>Scope confirmation: {{ project.scope_confirmed ? '100% confirmed' : 'still being reviewed' }}</small><div class="customer-project-details"><div><span>Requested visit</span><b>{{ project.requested_date }} · {{ project.requested_time }}</b></div><div><span>Job address</span><b>{{ project.address }}</b></div><section><span>Project details</span><p>{{ project.project_summary }}</p></section><section><span>Attachments</span><p>{{ project.uploads?.length ? project.uploads.map(file => file.filename).join(', ') : 'No files attached.' }}</p></section></div><div v-if="paymentStatus === 'paid'" class="payment-confirmed">Assessment payment recorded.</div><button v-else-if="paymentAvailable(project)" type="button" class="primary-button" @click="startDeposit" :disabled="sending">{{ sending ? 'Opening secure checkout…' : `Pay ${project.visit_fee_label || 'requested deposit'}` }} <span>↗</span></button><p v-if="paymentError" class="error">{{ paymentError }}</p><button type="button" class="virtual-button" @click="openVirtualMeet">▣ Start virtual meet-and-greet</button></div></form></section>
    </template>

    <div v-if="selectedInspiration" class="inspiration-lightbox" role="dialog" aria-modal="true" :aria-label="selectedInspiration.title" @click.self="closeInspiration"><button type="button" class="lightbox-close inspiration-lightbox-close" aria-label="Close image" @click="closeInspiration">×</button><button type="button" class="lightbox-arrow lightbox-previous" aria-label="Previous image" @click="moveInspiration(-1)">←</button><img :src="selectedInspiration.src" :alt="selectedInspiration.alt || selectedInspiration.title"/><button type="button" class="lightbox-arrow lightbox-next" aria-label="Next image" @click="moveInspiration(1)">→</button><div><span>{{ selectedInspiration.category || 'AI inspiration concept' }}</span><b>{{ selectedInspiration.title }}</b><small>{{ selectedInspiration.detail }}</small></div></div>

    <footer v-if="!isAdminPage" class="site-footer"><div class="footer-shell"><section class="footer-intro"><a class="footer-brand-link" href="/" @click.prevent="goHome"><img class="footer-logo" src="/lodex-logo-home-business.webp" alt="LODEX Home & Business Services"/></a><p>Residential and commercial property improvement services, including handyman repairs, maintenance, minor renovations, delivery and installation, furniture and equipment assembly, pressure washing, laser cleaning, and materials procurement.</p></section><nav class="footer-group"><span>Services</span><a v-for="service in services" :key="service.slug" :href="serviceHref(service)" @click.prevent="openService(service)">{{ service.short }}</a></nav><nav class="footer-group"><span>Your project</span><a href="/inspiration" @click.prevent="openInspirationGallery">Inspiration archive</a><a href="/#intake" @click.prevent="goHome('#intake')">Start a project</a><a href="/#project" @click.prevent="goHome('#project')">Open my project</a><a :href="phoneHref">Call {{ phone }}</a></nav><nav class="footer-group"><span>Legal</span><a href="/privacy" @click.prevent="navigate('/privacy')">Privacy Policy</a><a href="/terms" @click.prevent="navigate('/terms')">Terms & Conditions</a></nav><div class="footer-bottom"><span>© {{ new Date().getFullYear() }} LODEX. All rights reserved. · v{{ packageMetadata.version }}</span><span>Clear scope. Thoughtful work. No surprises.</span></div></div></footer>

    <button v-if="!isAdminPage" type="button" class="support-fab" :class="{ open: supportOpen }" @click="openSupport" :aria-expanded="supportOpen"><span>{{ supportOpen ? '×' : '✦' }}</span>{{ supportOpen ? 'Close' : 'Need help?' }}</button>
    <div v-if="supportOpen && !isAdminPage" class="support-popover"><div class="support-mascot" aria-hidden="true" style="display:flex;justify-content:flex-end;margin:-12px 0 -8px"><img src="/support/angry-support-bird.webp" alt="" width="88" height="132" style="width:88px;height:132px;object-fit:contain"/></div><p class="eyebrow">LODEX support</p><h3>What do you need?</h3><button v-for="service in services" :key="service.slug" type="button" @click="chooseService(service); supportOpen = false">{{ service.short }}</button><a :href="phoneHref" @click="supportOpen = false">Call {{ phone }}</a><form class="support-video-form" @submit.prevent="requestSupportCall"><input v-model="supportRequest.name" class="support-input" placeholder="Your name (optional)"/><input v-model="supportRequest.phone" class="support-input" type="tel" placeholder="Phone (optional)"/><input v-model="supportRequest.message" class="support-input" placeholder="What should we look at?"/><button type="submit">Request live video call</button></form><p v-if="supportStatus" class="support-status">{{ supportStatus }}</p><form @submit.prevent="send(); supportOpen = false"><input v-model="message" class="support-input" placeholder="Or ask a quick question…"/><button type="submit">Send</button></form></div>
    <div v-if="virtualOpen" class="virtual-modal" role="dialog" aria-modal="true" aria-label="Virtual meet-and-greet"><div class="virtual-header"><div><p class="eyebrow">LODEX virtual visit</p><h3>Meet from where the work is.</h3></div><button type="button" class="lightbox-close virtual-close" @click="closeVirtualMeet">×</button></div><div class="call-stage"><div class="remote-stage"><video ref="remoteVideoRef" autoplay playsinline></video><div v-if="!remoteConnected" class="waiting-state"><span>Waiting for LODEX to join</span><small>Room {{ virtualRoom }}</small></div><span class="video-label">LODEX</span></div><div class="local-stage"><div class="local-tile"><video ref="workVideoRef" autoplay playsinline muted></video><span>Work area</span></div><div class="local-tile"><video ref="localVideoRef" autoplay playsinline muted></video><span>You</span></div></div></div><p v-if="virtualStatus" class="virtual-status">{{ virtualStatus }}</p><p v-if="virtualError" class="virtual-error">{{ virtualError }}</p><div class="virtual-actions"><button v-if="!dualCamera" type="button" class="outline-button" @click="switchVirtualCamera">Switch camera</button><button type="button" class="outline-button" @click="copyVirtualInvite">Copy room invite</button><a class="primary-button" :href="phoneHref">Call LODEX</a><button type="button" class="back-button" @click="closeVirtualMeet">End virtual visit</button></div><small class="virtual-note">Your browser controls camera access. Dual-camera mode is attempted when the phone exposes two simultaneous camera devices; some mobile browsers allow only one camera at a time.</small></div>
  </main>
</template>
