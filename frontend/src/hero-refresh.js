const CORRECT_PHONE_DISPLAY = '(440) 601-8001'
const CORRECT_PHONE_HREF = 'tel:+14406018001'

const projectStarters = {
  Build: 'I want to build something for my home.',
  Fix: 'I need to fix something at my home.',
  Upgrade: 'I want to upgrade part of my home.',
  Customize: 'I want to customize something in my home.',
}

function setComposer(text = '') {
  const textarea = document.querySelector('.composer textarea')
  document.querySelector('#intake')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  if (!textarea) return
  textarea.value = text
  textarea.dispatchEvent(new Event('input', { bubbles: true }))
  textarea.focus()
}

function correctPhone(root = document) {
  root.querySelectorAll('a[href*="216-268-2990"], a[href*="2162682990"]').forEach(link => {
    link.href = CORRECT_PHONE_HREF
    link.textContent = link.textContent
      .replace('216-268-2990', CORRECT_PHONE_DISPLAY)
      .replace('(216) 268-2990', CORRECT_PHONE_DISPLAY)
  })

  const walker = document.createTreeWalker(root.body || root, NodeFilter.SHOW_TEXT)
  let node
  while ((node = walker.nextNode())) {
    if (node.nodeValue?.includes('216-268-2990')) node.nodeValue = node.nodeValue.replaceAll('216-268-2990', CORRECT_PHONE_DISPLAY)
  }
}

function refreshHero() {
  const hero = document.querySelector('#top.hero')
  if (!hero || hero.dataset.refreshed === 'true') return
  hero.dataset.refreshed = 'true'
  hero.classList.add('hero-refresh')
  hero.innerHTML = `
    <div class="hero-refresh-copy">
      <p class="eyebrow">LODEX · Northeast Ohio home projects</p>
      <h1>Whatcha tryna <em>do?</em></h1>
      <p class="hero-service-line">Build · Fix · Upgrade · Customize</p>
      <p class="hero-refresh-lede">From small repairs to custom fabrication and larger home projects. Tell us what you need, upload a photo or video, or schedule a visit.</p>

      <div class="hero-refresh-intents" aria-label="Choose project type">
        ${Object.keys(projectStarters).map(intent => `<button type="button" data-intent="${intent}">${intent}</button>`).join('')}
      </div>

      <div class="hero-refresh-actions">
        <button type="button" class="hero-primary" data-action="describe">Tell us about the project <span>↗</span></button>
        <button type="button" class="hero-secondary" data-action="show">Photo / video</button>
        <button type="button" class="hero-secondary" data-action="schedule">Schedule a visit</button>
      </div>
      <a class="hero-refresh-phone" href="${CORRECT_PHONE_HREF}">Prefer to talk? Call ${CORRECT_PHONE_DISPLAY}</a>

      <div class="popular-projects">
        <span>Popular projects</span>
        <p>Drywall & painting · Doors & trim · Pressure washing · Flooring · Tile · Cabinets · Custom fabrication · Repairs</p>
      </div>
    </div>

    <div class="hero-refresh-visual" aria-label="Examples of LODEX project work">
      <figure class="hero-shot hero-shot-main">
        <img src="https://lzcustom.com/assets/gallery/projects/kitchen-granite-hd.png" alt="Finished custom kitchen project" loading="eager" />
        <figcaption><b>Build & customize</b><span>Kitchens · cabinetry · surfaces</span></figcaption>
      </figure>
      <figure class="hero-shot hero-shot-small">
        <img src="https://lzcustom.com/assets/gallery/u6358423361_Professional_commercial_interior_painting_premium_fe294b7e-0227-404b-bed4-28fc32e6bb35_0.png" alt="Interior repair and finishing work" loading="eager" />
        <figcaption><b>Fix & upgrade</b><span>Repairs · finishes · improvements</span></figcaption>
      </figure>
      <div class="hero-proof">
        <strong>Show us the problem.</strong>
        <span>Photo, video, or your own words → we help determine the next step.</span>
      </div>
    </div>
  `

  hero.querySelectorAll('[data-intent]').forEach(button => {
    button.addEventListener('click', () => setComposer(projectStarters[button.dataset.intent] || ''))
  })
  hero.querySelector('[data-action="describe"]')?.addEventListener('click', () => setComposer())
  hero.querySelector('[data-action="show"]')?.addEventListener('click', () => {
    document.querySelector('#intake')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setTimeout(() => document.querySelector('.file-picker input[type="file"]')?.click(), 450)
  })
  hero.querySelector('[data-action="schedule"]')?.addEventListener('click', () => document.querySelector('.nav-cta')?.click())
}

export function enhanceLodexHero() {
  refreshHero()
  correctPhone()
  const observer = new MutationObserver(() => correctPhone())
  observer.observe(document.body, { childList: true, subtree: true })
}
