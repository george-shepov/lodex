import {
  INTAKE_DRAFT_KEY,
  appointmentPayloadFromDraft,
  buildIntakeDraft,
} from './intakeFormAssistant.mjs'

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

function setTextareaValue(textarea, value) {
  textarea.value = value
  textarea.dispatchEvent(new Event('input', { bubbles: true }))
}

function safeParse(value, fallback = {}) {
  try { return value ? JSON.parse(value) : fallback } catch { return fallback }
}

function loadIntakeDraft() {
  try { return safeParse(window.sessionStorage.getItem(INTAKE_DRAFT_KEY), {}) } catch { return {} }
}

function saveIntakeDraft(next) {
  const draft = { ...loadIntakeDraft(), ...next }
  try { window.sessionStorage.setItem(INTAKE_DRAFT_KEY, JSON.stringify(draft)) } catch {}
  return draft
}

function clearIntakeDraft() {
  try { window.sessionStorage.removeItem(INTAKE_DRAFT_KEY) } catch {}
}

function currentConversation() {
  return [...document.querySelectorAll('.messages article')].map(article => ({
    role: article.classList.contains('user') ? 'user' : 'assistant',
    text: article.textContent?.trim() || '',
  })).filter(turn => turn.text)
}

function currentServiceTitle() {
  const value = document.querySelector('.intake-copy b')?.textContent?.trim() || ''
  return /^(?:your project|general inquiry)$/i.test(value) ? '' : value
}

function currentDraft(extra = {}) {
  const draft = buildIntakeDraft({
    conversation: currentConversation(),
    serviceCategory: currentServiceTitle(),
    existing: loadIntakeDraft(),
    ...extra,
  })
  return saveIntakeDraft(draft)
}

function setFieldValue(field, value, eventName = 'input') {
  if (!field || value == null || value === '') return
  if (field.value === String(value)) return
  field.value = String(value)
  field.dispatchEvent(new Event(eventName, { bubbles: true }))
}

function scrollIntoUsefulView(element, block = 'start') {
  if (!element) return
  const rect = element.getBoundingClientRect()
  const visibleEnough = rect.top >= 8 && rect.bottom <= window.innerHeight - 8
  if (!visibleEnough) element.scrollIntoView({ behavior: 'smooth', block })
}

function installChatFirst() {
  if (window.location.pathname.replace(/\/$/, '') !== '') return
  const hero = document.querySelector('main > #top')
  const intake = document.querySelector('main > #intake')
  if (!hero || !intake || intake.nextElementSibling === hero) return
  hero.parentNode?.insertBefore(intake, hero)
}

function installComposerKeyboard() {
  document.querySelectorAll('.composer textarea').forEach(textarea => {
    if (textarea.dataset.lodexKeyboard === 'true') return
    textarea.dataset.lodexKeyboard = 'true'
    textarea.setAttribute('aria-keyshortcuts', 'Enter Control+Enter Meta+Enter')

    textarea.addEventListener('keydown', event => {
      if (event.key !== 'Enter' || event.isComposing) return

      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        const start = textarea.selectionStart ?? textarea.value.length
        const end = textarea.selectionEnd ?? start
        textarea.setRangeText('\n', start, end, 'end')
        textarea.dispatchEvent(new Event('input', { bubbles: true }))
        return
      }

      if (event.shiftKey) return
      event.preventDefault()
      textarea.closest('form')?.requestSubmit()
    })
  })
}

function installVoiceInput() {
  document.querySelectorAll('.composer').forEach(composer => {
    const textarea = composer.querySelector('textarea')
    if (!textarea || composer.querySelector('.voice-input-button')) return

    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'voice-input-button'
    button.setAttribute('aria-label', 'Start voice input')
    button.setAttribute('aria-pressed', 'false')
    button.title = 'Tap once to keep listening until you stop or send'
    button.innerHTML = `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z"></path>
        <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0"></path>
        <path d="M12 18v3"></path>
        <path d="M9 21h6"></path>
      </svg>
    `
    textarea.insertAdjacentElement('afterend', button)

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      button.disabled = true
      button.title = 'Voice input is not supported by this browser'
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = document.documentElement.lang || navigator.language || 'en-US'
    recognition.interimResults = true
    recognition.continuous = true
    recognition.maxAlternatives = 1

    let listeningDesired = false
    let recognitionActive = false
    let sessionBase = ''
    let restartTimer = null

    const updateUi = () => {
      button.classList.toggle('is-listening', listeningDesired)
      button.setAttribute('aria-pressed', listeningDesired ? 'true' : 'false')
      button.setAttribute('aria-label', listeningDesired ? 'Stop voice input' : 'Start voice input')
      button.title = listeningDesired
        ? 'Listening continuously… tap to stop or press Enter to send'
        : 'Tap once to keep listening until you stop or send'
    }

    const clearRestart = () => {
      if (restartTimer) window.clearTimeout(restartTimer)
      restartTimer = null
    }

    const startRecognition = () => {
      clearRestart()
      if (!listeningDesired || recognitionActive) return
      try { recognition.start() } catch {
        restartTimer = window.setTimeout(startRecognition, 180)
      }
    }

    const scheduleRestart = () => {
      clearRestart()
      if (!listeningDesired) return
      restartTimer = window.setTimeout(startRecognition, 140)
    }

    const stopVoice = () => {
      listeningDesired = false
      clearRestart()
      updateUi()
      if (recognitionActive) {
        try { recognition.stop() } catch {}
      }
    }

    recognition.onstart = () => {
      recognitionActive = true
      sessionBase = textarea.value
      updateUi()
    }

    recognition.onresult = event => {
      let transcript = ''
      for (let index = 0; index < event.results.length; index += 1) {
        const segment = event.results[index][0]?.transcript?.trim() || ''
        if (segment) transcript += `${transcript ? ' ' : ''}${segment}`
      }
      const spacer = sessionBase && transcript && !/\s$/.test(sessionBase) ? ' ' : ''
      setTextareaValue(textarea, `${sessionBase}${spacer}${transcript}`)
    }

    recognition.onend = () => {
      recognitionActive = false
      if (listeningDesired) scheduleRestart()
      else updateUi()
    }

    recognition.onerror = event => {
      recognitionActive = false
      const fatal = ['not-allowed', 'service-not-allowed', 'audio-capture'].includes(event.error)
      if (fatal) {
        listeningDesired = false
        clearRestart()
        updateUi()
        return
      }
      if (listeningDesired) scheduleRestart()
    }

    composer.addEventListener('submit', stopVoice, true)
    button.addEventListener('click', () => {
      textarea.focus()
      scrollIntoUsefulView(document.querySelector('.chat-card'))
      if (listeningDesired) {
        stopVoice()
        return
      }
      listeningDesired = true
      updateUi()
      startRecognition()
    })
  })
}

function installChatVisibility() {
  const intake = document.querySelector('#intake')
  if (!intake || intake.dataset.lodexChatVisibility === 'true') return
  intake.dataset.lodexChatVisibility = 'true'

  intake.addEventListener('focusin', event => {
    if (event.target?.closest?.('.composer')) scrollIntoUsefulView(document.querySelector('.chat-card'))
  })
  intake.addEventListener('submit', event => {
    if (event.target?.matches?.('.composer')) scrollIntoUsefulView(document.querySelector('.chat-card'))
  })
  intake.addEventListener('click', event => {
    if (!event.target?.closest?.('.service-chips button')) return
    window.setTimeout(() => scrollIntoUsefulView(document.querySelector('.chat-card')), 40)
  })
}

function updateDraftField(fieldName, value) {
  const trimmed = String(value || '').trim()
  const edits = {
    [fieldName]: trimmed,
    [`${fieldName}Edited`]: true,
  }
  saveIntakeDraft(edits)
}

function syncLiveIntakeForm() {
  const card = document.querySelector('.upload-card')
  const form = card?.querySelector('.intake-live-form')
  if (!form) return

  const draft = currentDraft()
  const service = form.querySelector('[data-draft-field="service"]')
  const summary = form.querySelector('[data-draft-field="summary"]')
  const location = form.querySelector('[data-draft-field="location"]')
  const timing = form.querySelector('[data-draft-field="timing"]')

  if (service && document.activeElement !== service) service.value = draft.service || 'We’ll infer this from the job'
  if (summary && document.activeElement !== summary) summary.value = draft.summary || ''
  if (location && document.activeElement !== location) location.value = draft.location || ''
  if (timing && document.activeElement !== timing) timing.value = draft.timing || ''
}

function installLiveIntakeForm() {
  const card = document.querySelector('.upload-card')
  if (!card) return

  if (!card.querySelector('.intake-live-form')) {
    const eyebrow = card.querySelector('.eyebrow')
    const heading = card.querySelector('h3')
    const intro = card.querySelector('h3 + p')
    if (eyebrow) eyebrow.textContent = 'Project form · filled with chat'
    if (heading) heading.textContent = 'We fill this in as you talk.'
    if (intro) intro.textContent = 'Watch the request take shape here. You can edit any field directly instead of answering another chat question.'

    const liveForm = document.createElement('div')
    liveForm.className = 'intake-live-form'
    liveForm.innerHTML = `
      <label class="intake-live-field intake-live-service">
        <span>Service</span>
        <input data-draft-field="service" readonly aria-label="Selected or inferred service" />
      </label>
      <label class="intake-live-field intake-live-full">
        <span>Project details</span>
        <textarea data-draft-field="summary" rows="5" placeholder="Chat will build the project description here…"></textarea>
      </label>
      <label class="intake-live-field">
        <span>Project / location</span>
        <input data-draft-field="location" placeholder="Home, business, room, or address" />
      </label>
      <label class="intake-live-field">
        <span>Preferred timing</span>
        <input data-draft-field="timing" placeholder="ASAP, tomorrow 7:30 AM, flexible…" />
      </label>
      <small>Chat is optional help. If it gets stuck, finish these fields directly and continue.</small>
    `

    const filePicker = card.querySelector('.file-picker')
    card.insertBefore(liveForm, filePicker || card.firstChild)

    liveForm.querySelector('[data-draft-field="summary"]')?.addEventListener('input', event => updateDraftField('summary', event.target.value))
    liveForm.querySelector('[data-draft-field="location"]')?.addEventListener('input', event => updateDraftField('location', event.target.value))
    liveForm.querySelector('[data-draft-field="timing"]')?.addEventListener('input', event => updateDraftField('timing', event.target.value))

    const mediaNotes = [...card.querySelectorAll('textarea')].find(textarea => !textarea.closest('.intake-live-form'))
    if (mediaNotes) mediaNotes.placeholder = 'Photo/video notes (optional)'
    const confirm = card.querySelector(':scope > .confirm')
    if (confirm) confirm.classList.add('legacy-intake-confirm')
    const ready = card.querySelector('.ready-button')
    if (ready) ready.innerHTML = 'Review & submit request <span>↗</span>'
  }

  syncLiveIntakeForm()
}

function addDirectEntryNotice(message) {
  const card = document.querySelector('.upload-card') || document.querySelector('.schedule-card')
  if (!card) return
  let notice = card.querySelector('.intake-direct-notice')
  if (!notice) {
    notice = document.createElement('div')
    notice.className = 'intake-direct-notice'
    card.prepend(notice)
  }
  notice.textContent = message || 'Chat is having trouble. No problem—finish the request form directly.'
  card.classList.add('needs-direct-entry')
  window.setTimeout(() => scrollIntoUsefulView(card, 'center'), 20)
}

function preferredTimeOption(select, value) {
  if (!select || !value) return
  const match = [...select.options].find(option => option.value === value)
  if (match) return
  const option = document.createElement('option')
  option.value = value
  option.textContent = value
  select.append(option)
}

function syncScheduleFromDraft() {
  const form = document.querySelector('.schedule-card')
  if (!form) return
  const draft = currentDraft()
  const address = form.querySelector('input[placeholder="Job address"]')
  const date = form.querySelector('input[type="date"]')
  const time = form.querySelector('select')

  if (address?.value) saveIntakeDraft({ location: address.value, locationEdited: true })
  else setFieldValue(address, draft.location)

  if (date?.value) saveIntakeDraft({ preferredDate: date.value })
  else setFieldValue(date, draft.preferredDate)

  if (draft.preferredTime) preferredTimeOption(time, draft.preferredTime)
  if (time?.value) saveIntakeDraft({ preferredTime: time.value })
  else setFieldValue(time, draft.preferredTime, 'change')
}

function installFinalReviewForm() {
  const form = document.querySelector('.schedule-card')
  if (!form) return

  if (!form.querySelector('.intake-review-block')) {
    const eyebrow = form.querySelector('.eyebrow')
    const heading = form.querySelector('h3')
    const intro = form.querySelector('h3 + p')
    if (eyebrow) eyebrow.textContent = 'Final review'
    if (heading) heading.textContent = 'Review the request, then send it.'
    if (intro) intro.textContent = 'The chat has already filled what it can. Correct anything below, add your contact details, and submit when it looks right.'

    const review = document.createElement('div')
    review.className = 'intake-review-block'
    review.innerHTML = `
      <div class="intake-review-service"><span>Service</span><b data-review-service></b></div>
      <label>
        <span>Project details</span>
        <textarea data-review-summary rows="6" required placeholder="Describe what you need LODEX to do"></textarea>
      </label>
    `
    const fields = form.querySelector('.fields')
    form.insertBefore(review, fields || form.firstChild)

    const consent = document.createElement('label')
    consent.className = 'intake-review-consent'
    consent.innerHTML = '<input type="checkbox" required data-review-confirm /> <span>I reviewed the project details above and want to submit this request to LODEX.</span>'
    const actions = form.querySelector('.schedule-actions')
    form.insertBefore(consent, actions || null)

    review.querySelector('[data-review-summary]')?.addEventListener('input', event => updateDraftField('summary', event.target.value))
    consent.querySelector('[data-review-confirm]')?.addEventListener('change', event => saveIntakeDraft({ confirmed: event.target.checked }))

    form.querySelector('input[placeholder="Job address"]')?.addEventListener('input', event => saveIntakeDraft({ location: event.target.value.trim(), locationEdited: true }))
    form.querySelector('input[type="date"]')?.addEventListener('input', event => saveIntakeDraft({ preferredDate: event.target.value }))
    form.querySelector('select')?.addEventListener('change', event => saveIntakeDraft({ preferredTime: event.target.value, timing: event.target.value, timingEdited: true }))

    form.addEventListener('submit', event => {
      const checkbox = form.querySelector('[data-review-confirm]')
      if (checkbox?.checked) {
        saveIntakeDraft({ confirmed: true })
        return
      }
      event.preventDefault()
      event.stopImmediatePropagation()
      checkbox?.focus()
      checkbox?.reportValidity?.()
    }, true)
  }

  const draft = currentDraft()
  const service = form.querySelector('[data-review-service]')
  const summary = form.querySelector('[data-review-summary]')
  const consent = form.querySelector('[data-review-confirm]')
  if (service) service.textContent = draft.service || 'General project request'
  if (summary && document.activeElement !== summary) summary.value = draft.summary || ''
  if (consent && document.activeElement !== consent) consent.checked = Boolean(draft.confirmed)
  syncScheduleFromDraft()

  if (draft.openReview) {
    saveIntakeDraft({ openReview: false })
    window.setTimeout(() => scrollIntoUsefulView(form, 'start'), 40)
  }
}

function installFlowLabels() {
  const labels = document.querySelectorAll('.flow span')
  if (labels.length < 3) return
  if (labels[0].textContent !== '1. Chat + form') labels[0].textContent = '1. Chat + form'
  if (labels[1].textContent !== '2. Review & submit') labels[1].textContent = '2. Review & submit'
  if (labels[2].textContent !== '3. Project details') labels[2].textContent = '3. Project details'
}

function installIntakeFetchBridge() {
  if (window.__lodexIntakeFetchBridgeInstalled) return
  window.__lodexIntakeFetchBridgeInstalled = true
  const previousFetch = window.fetch.bind(window)

  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || ''
    const isIntakeChat = /\/api\/intake\/chat(?:\?|$)/.test(url)
    const isAppointment = /\/api\/appointments\/request(?:\?|$)/.test(url)

    if (isAppointment && typeof init?.body === 'string') {
      try {
        const payload = JSON.parse(init.body)
        init = { ...init, body: JSON.stringify(appointmentPayloadFromDraft(payload, loadIntakeDraft())) }
      } catch {}
    }

    let response
    try {
      response = await previousFetch(input, init)
    } catch (error) {
      if (isIntakeChat) addDirectEntryNotice('Chat could not connect. Finish the project form directly and continue to review.')
      throw error
    }

    if (isIntakeChat) {
      if (!response.ok) {
        addDirectEntryNotice('Chat is having trouble. Finish the project form directly and continue to review.')
      } else {
        try {
          const data = await response.clone().json()
          const draft = currentDraft({ capturedAddress: data.captured_address || '' })
          if (data.ready_to_schedule) saveIntakeDraft({ ...draft, openReview: true })
          window.setTimeout(() => {
            syncLiveIntakeForm()
            installFinalReviewForm()
          }, 0)
        } catch {}
      }
    }

    if (isAppointment && response.ok) window.setTimeout(clearIntakeDraft, 250)
    return response
  }
}

function installBackToTop() {
  const sections = document.querySelectorAll('main > section, main > article.legal-page')
  sections.forEach(section => {
    if (section.querySelector(':scope > .section-back-to-top')) return
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'section-back-to-top'
    button.innerHTML = 'Back to top <span aria-hidden="true">↑</span>'
    button.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }))
    section.append(button)
  })
}

function installVoicePrivacyCopy() {
  if (window.location.pathname.replace(/\/$/, '') !== '/privacy') return
  document.querySelectorAll('.legal-content p').forEach(paragraph => {
    if (!paragraph.textContent.startsWith('Camera and microphone access begins only after')) return
    paragraph.textContent = 'Microphone access may begin after you choose the voice-input button in project intake and your browser grants permission. Camera and microphone access may also begin after you choose to start a virtual visit. Voice transcription may be handled by your browser or platform speech-recognition service under that provider’s terms. LODEX does not use the website code to retain raw intake-dictation audio. Your browser and device settings control permission access.'
  })
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
        status.textContent = `Saved: ${rating}/5 stars. Thank you.`
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
  installIntakeFetchBridge()

  const apply = () => {
    installFooterMark()
    installChatFirst()
    installComposerKeyboard()
    installVoiceInput()
    installChatVisibility()
    installLiveIntakeForm()
    installFinalReviewForm()
    installFlowLabels()
    installBackToTop()
    installVoicePrivacyCopy()
    installSurvey()
  }

  apply()
  const observer = new MutationObserver(apply)
  observer.observe(document.body, { childList: true, subtree: true })
}
