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
    button.setAttribute('aria-label', 'Speak your project details')
    button.setAttribute('aria-pressed', 'false')
    button.title = 'Speak instead of typing'
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
    recognition.continuous = false
    recognition.maxAlternatives = 1
    let listening = false
    let baseText = ''

    const stopListeningUi = () => {
      listening = false
      button.classList.remove('is-listening')
      button.setAttribute('aria-pressed', 'false')
      button.setAttribute('aria-label', 'Speak your project details')
      button.title = 'Speak instead of typing'
    }

    recognition.onstart = () => {
      listening = true
      baseText = textarea.value
      button.classList.add('is-listening')
      button.setAttribute('aria-pressed', 'true')
      button.setAttribute('aria-label', 'Stop voice input')
      button.title = 'Listening… tap to stop'
    }

    recognition.onresult = event => {
      let transcript = ''
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        transcript += event.results[index][0]?.transcript || ''
      }
      const spacer = baseText && transcript && !/\s$/.test(baseText) ? ' ' : ''
      setTextareaValue(textarea, `${baseText}${spacer}${transcript}`)
    }

    recognition.onend = stopListeningUi
    recognition.onerror = stopListeningUi

    button.addEventListener('click', () => {
      textarea.focus()
      if (listening) {
        recognition.stop()
        return
      }
      try {
        recognition.start()
      } catch {
        stopListeningUi()
      }
    })
  })
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
  const apply = () => {
    installFooterMark()
    installChatFirst()
    installComposerKeyboard()
    installVoiceInput()
    installBackToTop()
    installVoicePrivacyCopy()
    installSurvey()
  }
  apply()
  const observer = new MutationObserver(apply)
  observer.observe(document.body, { childList: true, subtree: true })
}
