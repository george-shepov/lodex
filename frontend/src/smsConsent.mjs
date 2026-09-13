export const SMS_CONSENT_TEXT = 'I agree to receive service-related SMS/MMS messages from LODEX at the mobile number provided. Message frequency varies. Message and data rates may apply. Reply STOP to opt out or HELP for assistance. Consent is not a condition of purchase.'

let consentSequence = 0

function createLink(documentRef, href, text) {
  const link = documentRef.createElement('a')
  link.href = href
  link.textContent = text
  return link
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
  checkbox.addEventListener('change', () => {
    input.dataset.smsConsent = checkbox.checked ? 'true' : 'false'
  })

  return true
}

export function scanForPhoneInputs(root, documentRef = root?.ownerDocument || root) {
  if (!root || !documentRef) return 0

  const inputs = []
  if (root.matches?.('input[type="tel"]')) inputs.push(root)
  if (root.querySelectorAll) inputs.push(...root.querySelectorAll('input[type="tel"]'))

  let attached = 0
  for (const input of inputs) {
    if (attachSmsConsentToPhoneInput(input, documentRef)) attached += 1
  }
  return attached
}

export function installSmsConsent(documentRef, MutationObserverClass = globalThis.MutationObserver) {
  if (!documentRef) return () => {}

  scanForPhoneInputs(documentRef, documentRef)
  if (!MutationObserverClass || !documentRef.body) return () => {}

  const observer = new MutationObserverClass(mutations => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes || []) {
        if (node?.nodeType === 1) scanForPhoneInputs(node, documentRef)
      }
    }
  })

  observer.observe(documentRef.body, { childList: true, subtree: true })
  return () => observer.disconnect()
}
