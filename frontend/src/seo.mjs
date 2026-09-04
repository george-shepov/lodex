export const SITE_URL = 'https://lodex.work'
export const SITE_NAME = 'LODEX Home & Business Services'
export const SOCIAL_IMAGE = `${SITE_URL}/lodex-logo-home-business.webp`
export const BUSINESS_ID = `${SITE_URL}/#business`

const home = {
  path: '/',
  kind: 'home',
  title: 'LODEX | Handyman & Property Services in Northeast Ohio',
  description: 'LODEX coordinates handyman repairs, renovations, installations, cleaning, restoration, and property services across Northeast Ohio.',
  h1: 'One call. Real progress.',
  intro: 'From repairs and maintenance to delivery, installation, cleanup, restoration, and larger improvements, LODEX gives you one local point of contact and a clear next step.',
}

export const SERVICE_ROUTES = [
  {
    path: '/services/contracting-renovations', slug: 'contracting-renovations', kind: 'service',
    title: 'General Contracting & Renovations | LODEX Northeast Ohio',
    description: 'Plan and coordinate room remodels, property refreshes, structural updates, finishes, built-ins, and skilled trades with LODEX in Northeast Ohio.',
    h1: 'General Contracting & Renovations',
    intro: 'Bring the bigger picture. We help turn it into a practical plan, coordinate the right work, and keep the details moving.',
    includes: ['Room remodels and refreshes', 'Project planning and trade coordination', 'Structural and finish updates', 'Built-ins, cabinetry, and custom improvements'],
    useCases: ['Kitchen, bath, basement, and office upgrades', 'A property refresh before move-in', 'A larger scope needing one point of coordination'],
    image: '/services/renovation-project-planning.webp',
  },
  {
    path: '/services/handyman-maintenance', slug: 'handyman-maintenance', kind: 'service',
    title: 'Handyman & Property Maintenance | LODEX Northeast Ohio',
    description: 'Book practical repairs, punch lists, fixture updates, drywall, paint, caulking, doors, trim, and seasonal property maintenance in Northeast Ohio.',
    h1: 'Handyman & Property Maintenance',
    intro: 'The work that keeps a property working well—without turning a small issue into a weeks-long project.',
    includes: ['Repairs, adjustments, and punch lists', 'Fixture, hardware, and TV installation', 'Doors, trim, drywall, paint, and caulking', 'Seasonal and ongoing property care'],
    useCases: ['Fixes before guests, tenants, or a sale', 'A recurring maintenance partner', 'A repair you can show in a photo or short video'],
    image: '/services/handyman-tools.webp',
  },
  {
    path: '/services/white-glove-installation', slug: 'white-glove-installation', kind: 'service',
    title: 'Delivery, Assembly & Installation | LODEX Northeast Ohio',
    description: 'Get careful pickup, delivery, assembly, placement, testing, and packaging cleanup for furniture, equipment, appliances, and electronics.',
    h1: 'White-Glove Delivery & Installation',
    intro: 'We handle the last mile with care: the right item, in the right place, assembled, tested, and cleared of packaging.',
    includes: ['Furniture and commercial fixture assembly', 'Fitness equipment setup and placement', 'Appliance and electronics installation', 'Packaging and debris removal'],
    useCases: ['A new home, office, rental, or gym setup', 'A delivery requiring skilled assembly', 'High-attention equipment needing a finished handoff'],
    image: '/services/tv-wall-installation.webp',
  },
  {
    path: '/services/shopping-sourcing', slug: 'shopping-sourcing', kind: 'service',
    title: 'Materials Sourcing & Procurement | LODEX Northeast Ohio',
    description: 'Let LODEX research, compare, match, purchase, pick up, and deliver fixtures, hardware, finishes, parts, and project materials.',
    h1: 'Shopping, Sourcing & Procurement',
    intro: 'Need a matching part, the right fixture, or someone to collect materials and bring them to the job? Start with what you need done.',
    includes: ['Material and hardware pickup', 'Product research and option comparison', 'Fixture, part, and finish matching', 'Purchase coordination and job-site delivery'],
    useCases: ['You know the outcome but not the exact part', 'Materials must be gathered before work starts', 'Dependable local procurement support'],
    image: '/services/materials-procurement.webp',
  },
  {
    path: '/services/cleaning-restoration', slug: 'cleaning-restoration', kind: 'service',
    title: 'Pressure Washing & Laser Cleaning | LODEX Northeast Ohio',
    description: 'Match the method to the surface with exterior pressure washing, property cleanup, and targeted laser cleaning and restoration services.',
    h1: 'Cleaning & Surface Restoration',
    intro: 'From a fresh exterior to a delicate restoration job, we match the cleaning method to the surface and desired result.',
    includes: ['Exterior pressure washing', 'Move-in, project, and general cleanup', 'Laser cleaning for rust, coatings, and restoration'],
    useCases: ['Exterior, patio, driveway, or concrete cleaning', 'Cleanup before a property’s next use', 'Specialty surfaces needing careful restoration'],
    image: '/services/pressure-washing-wide.webp',
  },
  {
    path: '/services/turnkey-rental-launch', slug: 'turnkey-rental-launch', kind: 'service',
    title: 'Turnkey Rental & Property Launch | LODEX Northeast Ohio',
    description: 'Coordinate renovation, appliances, furniture, delivery, setup, cleaning, punch lists, and a rent-ready property handoff through LODEX.',
    h1: 'Turnkey Rental / Property Launch',
    intro: 'Coordinate renovation, furnishings, installation, cleaning, and the final punch list through one practical property-launch scope.',
    includes: ['Renovation, repair, and final punch list', 'Appliances, furniture, delivery, and installation', 'Wi-Fi, smart locks, cleaning, and setup', 'Rent-ready handoff with one coordinated plan'],
    useCases: ['Essential launches starting around $25,000', 'Premium launches starting around $35,000', 'Signature launches starting around $50,000'],
    image: '/services/renovation-project-planning.webp',
  },
  {
    path: '/services/inspection-ready', slug: 'inspection-ready', kind: 'service',
    title: 'HCV & Section 8 Inspection Preparation | LODEX Ohio',
    description: 'Prepare rental property for HCV or Section 8 inspections with a walkthrough, repair punch list, cleanup, remediation, and photo documentation.',
    h1: 'Voucher / Section 8 / HCV Inspection-Ready',
    intro: 'We help owners prepare a property for inspection with practical walkthrough and remediation support. LODEX does not certify or approve compliance.',
    includes: ['Smoke and CO detector safety punch lists', 'Doors, windows, locks, paint, and patching', 'Appliance checks, cleanup, and repair coordination', 'Photo documentation and inspection preparation'],
    useCases: ['Voucher or HCV inspection preparation', 'Repairs before a scheduled inspection', 'A final documented property punch list'],
    image: '/services/handyman-tools.webp',
  },
  {
    path: '/services/corporate-housing', slug: 'corporate-housing', kind: 'service',
    title: 'Corporate & Workforce Housing Setup | LODEX Ohio',
    description: 'Set up and operate corporate or workforce housing with renovation, furnishings, appliances, Wi-Fi, access control, cleaning, and maintenance.',
    h1: 'LODEX Corporate Housing',
    intro: 'Acquire it. Renovate it. Furnish it. House your team with one coordinated setup and ongoing property-operations plan.',
    includes: ['Renovation and durable finish programs', 'Beds, desks, TVs, appliances, and furnishings', 'Wi-Fi, access control, and smart locks', 'Recurring cleaning, maintenance, and turnover'],
    useCases: ['Workforce and project housing', 'Corporate employee homes', 'Repeat property setup and operations'],
    image: '/services/materials-procurement.webp',
  },
]

const otherRoutes = [
  {
    path: '/inspiration', kind: 'collection',
    title: 'Property Improvement Inspiration | LODEX Northeast Ohio',
    description: 'Explore clearly labeled AI-generated renovation, installation, finish, and property-improvement concepts, then turn an idea into a practical scope.',
    h1: 'Find the detail that starts your project.',
    intro: 'This inspiration library is not a claim of completed LODEX work. Show us the idea and your real space, and we will help translate the direction into a practical scope.',
  },
  {
    path: '/privacy', kind: 'legal',
    title: 'Privacy Policy | LODEX Home & Business Services',
    description: 'Read how LODEX collects, uses, protects, and retains project, contact, upload, scheduling, payment, and website activity information.',
    h1: 'Privacy Policy',
    intro: 'This policy explains what LODEX collects through this website, how we use it, and the choices available to you.',
    paragraphs: ['LODEX collects information you choose to provide when describing a project, uploading media, requesting a visit, opening a project record, or making a requested deposit.', 'Information is used to evaluate and coordinate service, communicate about next steps, operate the website, process requested payments, and meet legitimate legal and business obligations.', 'You may ask to review, correct, or delete information you provided, subject to identity verification and records that LODEX must or may lawfully retain.'],
  },
  {
    path: '/terms', kind: 'legal',
    title: 'Website Terms & Conditions | LODEX',
    description: 'Review the terms governing use of the LODEX website, project requests, uploads, AI-assisted intake, scheduling, payments, and service information.',
    h1: 'Terms & Conditions',
    intro: 'These terms govern use of the LODEX website. A separate written quote, work order, or agreement controls the actual services for a project.',
    paragraphs: ['Website descriptions, chat responses, automated analysis, and scheduling requests are informational and do not create a final quote, schedule, scope, or contract.', 'Service availability depends on the project, location, site conditions, materials, staffing, licensing, and permit requirements.', 'Customers must provide accurate project and access information and review the confirmed scope, materials, price, and project-specific terms before work begins.'],
  },
]

export const PUBLIC_ROUTES = [home, ...SERVICE_ROUTES, ...otherRoutes]

function normalizePath(pathname = '/') {
  const clean = pathname.split('?')[0].split('#')[0] || '/'
  if (clean === '/') return clean
  return clean.replace(/\/+$/, '') || '/'
}

export function routeForPath(pathname) {
  const path = normalizePath(pathname)
  return PUBLIC_ROUTES.find(route => route.path === path) || null
}

export function canonicalForPath(pathname) {
  const route = routeForPath(pathname)
  return route ? `${SITE_URL}${route.path === '/' ? '/' : route.path}` : null
}

export function structuredDataForRoute(route) {
  if (!route) return null
  const business = {
    '@type': 'HomeAndConstructionBusiness', '@id': BUSINESS_ID, name: SITE_NAME,
    url: `${SITE_URL}/`, logo: SOCIAL_IMAGE, image: SOCIAL_IMAGE,
    telephone: '+1-440-601-8001', description: home.description,
    areaServed: { '@type': 'AdministrativeArea', name: 'Northeast Ohio' },
  }
  const website = {
    '@type': 'WebSite', '@id': `${SITE_URL}/#website`, name: SITE_NAME,
    url: `${SITE_URL}/`, publisher: { '@id': BUSINESS_ID },
  }
  if (route.kind === 'home') {
    return { '@context': 'https://schema.org', '@graph': [business, website] }
  }
  const page = {
    '@type': route.kind === 'collection' ? 'CollectionPage' : 'WebPage',
    '@id': `${SITE_URL}${route.path}#webpage`, url: `${SITE_URL}${route.path}`,
    name: route.title, description: route.description,
    isPartOf: { '@id': `${SITE_URL}/#website` },
  }
  if (route.kind !== 'service') return { '@context': 'https://schema.org', '@graph': [business, website, page] }
  return { '@context': 'https://schema.org', '@graph': [business, website, page, {
    '@type': 'Service', '@id': `${SITE_URL}${route.path}#service`, name: route.h1,
    description: route.description, url: `${SITE_URL}${route.path}`,
    image: `${SITE_URL}${route.image}`, provider: { '@id': BUSINESS_ID },
    areaServed: { '@type': 'AdministrativeArea', name: 'Northeast Ohio' },
  }, {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: `${SITE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Services', item: `${SITE_URL}/#services` },
      { '@type': 'ListItem', position: 3, name: route.h1, item: `${SITE_URL}${route.path}` },
    ],
  }] }
}

function setMeta(selector, attributes) {
  let element = document.head.querySelector(selector)
  if (!element) {
    element = document.createElement('meta')
    document.head.appendChild(element)
  }
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value)
}

export function applyRouteSeo(pathname) {
  const route = routeForPath(pathname)
  const path = normalizePath(pathname)
  const isPrivate = path === '/admin' || path.startsWith('/designs/')
  const effective = route || {
    title: isPrivate ? `Private workspace | ${SITE_NAME}` : `Page not found | ${SITE_NAME}`,
    description: isPrivate ? 'Private LODEX application workspace.' : 'The requested LODEX page could not be found.',
    kind: 'private',
  }
  document.title = effective.title
  setMeta('meta[name="description"]', { name: 'description', content: effective.description })
  setMeta('meta[name="robots"]', { name: 'robots', content: route ? 'index,follow' : 'noindex,nofollow' })
  setMeta('meta[property="og:type"]', { property: 'og:type', content: 'website' })
  setMeta('meta[property="og:site_name"]', { property: 'og:site_name', content: SITE_NAME })
  setMeta('meta[property="og:title"]', { property: 'og:title', content: effective.title })
  setMeta('meta[property="og:description"]', { property: 'og:description', content: effective.description })
  setMeta('meta[property="og:image"]', { property: 'og:image', content: SOCIAL_IMAGE })
  setMeta('meta[property="og:image:alt"]', { property: 'og:image:alt', content: SITE_NAME })
  setMeta('meta[name="twitter:card"]', { name: 'twitter:card', content: 'summary_large_image' })
  setMeta('meta[name="twitter:title"]', { name: 'twitter:title', content: effective.title })
  setMeta('meta[name="twitter:description"]', { name: 'twitter:description', content: effective.description })
  setMeta('meta[name="twitter:image"]', { name: 'twitter:image', content: SOCIAL_IMAGE })

  const canonical = canonicalForPath(pathname)
  let canonicalLink = document.head.querySelector('link[rel="canonical"]')
  if (canonical) {
    if (!canonicalLink) {
      canonicalLink = document.createElement('link')
      canonicalLink.rel = 'canonical'
      document.head.appendChild(canonicalLink)
    }
    canonicalLink.href = canonical
    setMeta('meta[property="og:url"]', { property: 'og:url', content: canonical })
  } else {
    canonicalLink?.remove()
    document.head.querySelector('meta[property="og:url"]')?.remove()
  }

  let schema = document.head.querySelector('#lodex-structured-data')
  const structuredData = structuredDataForRoute(route)
  if (structuredData) {
    if (!schema) {
      schema = document.createElement('script')
      schema.id = 'lodex-structured-data'
      schema.type = 'application/ld+json'
      document.head.appendChild(schema)
    }
    schema.textContent = JSON.stringify(structuredData)
  } else {
    schema?.remove()
  }
}
