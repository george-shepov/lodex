import { lodexVideoSrc } from './lodex-video/index.js'

const replayDelayMs = 5000
let replayTimer = null

function installBrandVideo() {
  const hero = document.querySelector('.hero-visual')
  if (!hero || hero.querySelector('.lodex-brand-loop')) return
  const target = hero.querySelector('.hero-image-main')
  if (!target) return

  const video = document.createElement('video')
  video.className = 'lodex-brand-loop'
  video.src = lodexVideoSrc
  video.autoplay = true
  video.muted = true
  video.playsInline = true
  video.preload = 'auto'
  video.setAttribute('aria-label', 'LODEX animated brand sign')
  video.addEventListener('ended', () => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    clearTimeout(replayTimer)
    replayTimer = window.setTimeout(() => {
      video.currentTime = 0
      video.play().catch(() => {})
    }, replayDelayMs)
  })
  target.replaceWith(video)
  video.play().catch(() => {})
}

function installFooterMark() {
  const link = document.querySelector('.footer-brand-link')
  if (!link || link.querySelector('.footer-wordmark')) return
  link.querySelector('.footer-logo')?.remove()
  const mark = document.createElement('span')
  mark.className = 'footer-wordmark'
  mark.innerHTML = '<strong>LODEX</strong><small>Residential · Commercial · Property Services</small>'
  link.append(mark)
}

function getLookupValue(selector) {
  return document.querySelector(selector)?.value?.trim() || ''
}

function installSurvey() {
  document.querySelectorAll('.project-result').forEach(projectResult => {
    if (projectResult.querySelector('.customer-survey')) return

    const form = document.createElement('form')
    form.className = 'customer-survey'
    form.innerHTML = `
      <div class="survey-head"><span>How did we do?</span><b>Rate your LODEX experience</b></div>
      <div class="survey-stars" role="radiogroup" aria-label="Overall rating">
        ${[1,2,3,4,5].map(n => `<button type="button" data-rating="${n}" aria-label="${n} star${n > 1 ? 's' : ''}">★</button>`).join('')}
      </div>
      <div class="survey-recommend"><span>Would you recommend LODEX?</span><button type="button" data-recommend="true">Yes</button><button type="button" data-recommend="false">Not yet</button></div>
      <textarea name="comments" maxlength="2000" placeholder="What went well, or what could be better?"></textarea>
      <div class="survey-actions"><button class="survey-submit" type="submit" disabled>Send feedback</button><small class="survey-status"></small></div>
    `

    let rating = 0
    let recommend = null
    const submit = form.querySelector('.survey-submit')
    const status = form.querySelector('.survey-status')
    const stars = [...form.querySelectorAll('[data-rating]')]

    stars.forEach(button => button.addEventListener('click', () => {
      rating = Number(button.dataset.rating)
      stars.forEach(star => star.classList.toggle('selected', Number(star.dataset.rating) <= rating))
      submit.disabled = false
    }))
    form.querySelectorAll('[data-recommend]').forEach(button => button.addEventListener('click', () => {
      recommend = button.dataset.recommend === 'true'
      form.querySelectorAll('[data-recommend]').forEach(item => item.classList.toggle('selected', item === button))
    }))

    form.addEventListener('submit', async event => {
      event.preventDefault()
      if (!rating) return
      submit.disabled = true
      status.textContent = 'Sending…'
      try {
        const response = await fetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_code: getLookupValue('.lookup-card input[placeholder="LDX-123456"]') || 'PROJECT',
            phone: getLookupValue('.lookup-card input[type="tel"]'),
            rating,
            recommend,
            comments: form.elements.comments.value.trim(),
          }),
        })
        if (!response.ok) throw new Error('Feedback could not be saved.')
        status.textContent = 'Thank you — feedback saved.'
        form.classList.add('submitted')
      } catch (error) {
        status.textContent = error.message
        submit.disabled = false
      }
    })

    projectResult.append(form)
  })
}

export function installLodexEnhancements() {
  const apply = () => {
    installBrandVideo()
    installFooterMark()
    installSurvey()
  }
  apply()
  const observer = new MutationObserver(apply)
  observer.observe(document.body, { childList: true, subtree: true })
}
