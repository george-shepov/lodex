export const SMS_CONSENT_VERSION = '2026-09-13-v1'
export const SMS_CONSENT_TEXT = 'I agree to receive service-related SMS/MMS messages from LODEX at the mobile number provided. Message frequency varies. Message and data rates may apply. Reply STOP to opt out or HELP for assistance. Consent is not a condition of purchase.'

export const PHONE_INPUT_SELECTOR = 'input[type="tel"], input[autocomplete="tel"], input[placeholder*="phone" i]'

let consentSequence = 0

function createLink(documentRef, href, text) {
  const link = documentRef.createElement('a')
  link.href = href
  link.textContent = text
  return link
}

function normalizePhone(value = '') {
  return String(value).replace(/\D/g, '')
}

function sourceFormName(form) {
  if (!form) return 'phone_field'
  if (form.dataset?.smsConsentSource) return form.dataset.smsConsentSource
  if (form.id) return form.id
  if (form.getAttribute?.('name')) return form.getAttribute('name')
  const firstClass = [...(form.classList || [])][0]
  return firstClass || 'phone_form'
}

export async function sendSmsConsentAudit(input, documentRef = input?.ownerDocument, formOverride = null) {
  if (!input || !documentRef) return false
  const checkboxId = input.dataset.smsConsentCheckbox
  const checkbox = checkboxId ? documentRef.getElementById(checkboxId) : null
  if (!checkbox?.checked) return false

  const phone = String(input.value || '').trim()
  const normalizedPhone = normalizePhone(phone)
  if (normalizedPhone.length < 7) return false

  const auditKey = `${normalizedPhone}:${SMS_CONSENT_VERSION}`
  if (checkbox.dataset.smsConsentAuditKey === auditKey) return true

  const windowRef = documentRef.defaultView
  if (!windowRef?.fetch) return false
  const form = formOverride || input.closest('form')

  try {
    const response = await windowRef.fetch('/api/sms/consent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      keepalive: true,
      body: JSON.stringify({
        phone,
        consent: true,
        source_form: sourceFormName(form),
        source_path: windowRef.location?.pathname || '/',
        consent_text: SMS_CONSENT_TEXT,
        consent_version: SMS_CONSENT_VERSION,
      }),
    })
    if (!response.ok) return false
    checkbox.dataset.smsConsentAuditKey = auditKey
    return true
  } catch {
    return false
  }
}

export function attachSmsConsentToPhoneInput(input, documentRef = input?.ownerDocument) {
  if (!input || !documentRef || input.dataset.smsConsentAttached === 'true') return false

  const anchor = input.closest('label') || input
  const wrapper = documentRef.createElement('div')
  wrapper.className = 'sms-consent-field'
  wrapper.dataset.smsConsent = ''

  const choice = documentRef.createElement('label')
  choice.className = 'sms-consent-choice'

  const checkbox = documentRef.createElement('input')
  checkbox.type = 'checkbox'
  checkbox.name = 'sms_consent'
  checkbox.value = 'yes'
  checkbox.checked = false
  checkbox.required = false
  checkbox.autocomplete = 'off'
  checkbox.id = `lodex-sms-consent-${++consentSequence}`

  const copy = documentRef.createElement('span')
  copy.textContent = SMS_CONSENT_TEXT

  choice.append(checkbox, copy)

  const links = documentRef.createElement('span')
  links.className = 'sms-consent-links'
  links.append(
    createLink(documentRef, '/privacy', 'Privacy Policy'),
    documentRef.createTextNode(' · '),
    createLink(documentRef, '/terms', 'Terms & Conditions'),
  )

  wrapper.append(choice, links)
  anchor.insertAdjacentElement('afterend', wrapper)

  input.dataset.smsConsentAttached = 'true'
  input.dataset.smsConsent = 'false'
  input.dataset.smsConsentCheckbox = checkbox.id

  const tryAudit = () => {
    if (checkbox.checked) void sendSmsConsentAudit(input, documentRef)
  }
  checkbox.addEventListener('change', () => {
    input.dataset.smsConsent = checkbox.checked ? 'true' : 'false'
    tryAudit()
  })
  input.addEventListener('change', tryAudit)
  input.addEventListener('blur', tryAudit)

  return true
}

export function scanForPhoneInputs(root, documentRef = root?.ownerDocument || root) {
  if (!root || !documentRef) return 0

  const inputs = []
  if (root.matches?.(PHONE_INPUT_SELECTOR)) inputs.push(root)
  if (root.querySelectorAll) inputs.push(...root.querySelectorAll(PHONE_INPUT_SELECTOR))

  let attached = 0
  for (const input of inputs) {
    if (attachSmsConsentToPhoneInput(input, documentRef)) attached += 1
  }
  return attached
}

export function installSmsConsent(documentRef, MutationObserverClass = globalThis.MutationObserver) {
  if (!documentRef) return () => {}

  scanForPhoneInputs(documentRef, documentRef)

  const handleSubmit = event => {
    const form = event.target
    if (!form?.querySelectorAll) return
    for (const input of form.querySelectorAll(PHONE_INPUT_SELECTOR)) {
      void sendSmsConsentAudit(input, documentRef, form)
    }
  }
  documentRef.addEventListener?.('submit', handleSubmit, true)

  if (!MutationObserverClass || !documentRef.body) {
    return () => documentRef.removeEventListener?.('submit', handleSubmit, true)
  }

  const observer = new MutationObserverClass(mutations => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes || []) {
        if (node?.nodeType === 1) scanForPhoneInputs(node, documentRef)
      }
    }
  })

  observer.observe(documentRef.body, { childList: true, subtree: true })
  return () => {
    observer.disconnect()
    documentRef.removeEventListener?.('submit', handleSubmit, true)
  }
}
