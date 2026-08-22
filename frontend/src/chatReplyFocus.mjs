const STATE_KEY = 'lodex-chat-return-position'

function safeParse(value, fallback = null) {
  try { return value ? JSON.parse(value) : fallback } catch { return fallback }
}

function saveReturnPosition() {
  const state = {
    x: window.scrollX,
    y: window.scrollY,
    activeSelector: document.activeElement?.matches?.('input, textarea, select, button')
      ? describeElement(document.activeElement)
      : '',
    savedAt: Date.now(),
  }
  try { window.sessionStorage.setItem(STATE_KEY, JSON.stringify(state)) } catch {}
  return state
}

function loadReturnPosition() {
  try { return safeParse(window.sessionStorage.getItem(STATE_KEY), null) } catch { return null }
}

function clearReturnPosition() {
  try { window.sessionStorage.removeItem(STATE_KEY) } catch {}
}

function describeElement(element) {
  if (!element) return ''
  if (element.id) return `#${CSS.escape(element.id)}`
  if (element.name) return `${element.tagName.toLowerCase()}[name="${CSS.escape(element.name)}"]`
  const placeholder = element.getAttribute?.('placeholder')
  if (placeholder) return `${element.tagName.toLowerCase()}[placeholder="${CSS.escape(placeholder)}"]`
  return ''
}

function makeReturnButton(state) {
  document.querySelector('.lodex-chat-return')?.remove()

  const button = document.createElement('button')
  button.type = 'button'
  button.className = 'lodex-chat-return'
  button.textContent = '↩ Back to where I was'
  button.setAttribute('aria-label', 'Return to your previous place on the page')

  Object.assign(button.style, {
    position: 'fixed',
    right: '16px',
    bottom: '18px',
    zIndex: '2147483000',
    border: '1px solid rgba(255,255,255,.18)',
    borderRadius: '999px',
    padding: '11px 15px',
    font: '600 14px/1.1 system-ui, sans-serif',
    color: '#fff',
    background: 'rgba(18,18,18,.92)',
    boxShadow: '0 10px 30px rgba(0,0,0,.28)',
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
    cursor: 'pointer',
  })

  const restore = () => {
    window.scrollTo({ left: state.x || 0, top: state.y || 0, behavior: 'smooth' })
    if (state.activeSelector) {
      window.setTimeout(() => document.querySelector(state.activeSelector)?.focus?.({ preventScroll: true }), 420)
    }
    clearReturnPosition()
    button.remove()
  }

  button.addEventListener('click', restore)
  document.body.append(button)
}

function latestAssistantMessage(messages) {
  return [...messages.querySelectorAll('article')]
    .reverse()
    .find(article => !article.classList.contains('user')) || null
}

function revealReply(messages) {
  const state = loadReturnPosition()
  if (!state || Date.now() - Number(state.savedAt || 0) > 45000) return

  const reply = latestAssistantMessage(messages)
  if (!reply) return

  requestAnimationFrame(() => {
    reply.scrollIntoView({ behavior: 'smooth', block: 'center' })
    makeReturnButton(state)
  })
}

export function installChatReplyFocus() {
  const intake = document.querySelector('#intake')
  const messages = intake?.querySelector('.messages')
  if (!intake || !messages || intake.dataset.lodexReplyFocus === 'true') return
  intake.dataset.lodexReplyFocus = 'true'

  intake.addEventListener('submit', event => {
    if (!event.target?.matches?.('.composer')) return
    saveReturnPosition()
  }, true)

  let previousAssistantCount = messages.querySelectorAll('article:not(.user)').length
  const observer = new MutationObserver(() => {
    const currentCount = messages.querySelectorAll('article:not(.user)').length
    if (currentCount <= previousAssistantCount) return
    previousAssistantCount = currentCount
    revealReply(messages)
  })

  observer.observe(messages, { childList: true, subtree: true })
}
