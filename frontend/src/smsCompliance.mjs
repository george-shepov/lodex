export const SMS_COMPLIANCE_EFFECTIVE_DATE = 'September 13, 2026'

export const SMS_COMPLIANCE = {
  '/privacy': {
    title: 'SMS messaging and mobile information',
    paragraphs: [
      'LODEX may send service-related SMS or MMS messages only to customers who have expressly opted in to receive text messages. Messages may include replies to inquiries, appointment confirmations and scheduling updates, estimates, project or service updates, invoice or payment notifications, and other communications directly related to services requested by the customer. Message frequency varies based on customer activity and service needs. Message and data rates may apply. Reply STOP to opt out or HELP for assistance.',
      'LODEX does not sell, rent, share, or provide mobile phone numbers, SMS opt-in information, or messaging consent data to third parties or affiliates for marketing or promotional purposes. Mobile information may be provided only to communications service providers and other vendors as reasonably necessary to deliver requested messaging services, or when required by law. Text-messaging originator opt-in data and consent will not be shared with third parties or affiliates for their own marketing or promotional use.',
    ],
  },
  '/terms': {
    title: 'SMS messaging terms',
    paragraphs: [
      'By expressly opting in, you agree to receive service-related SMS or MMS messages from LODEX at the mobile number you provide. Messages may include responses to inquiries, appointment confirmations, scheduling updates, estimates, project or service updates, invoice or payment notifications, and other customer-care communications related to services you requested. Message frequency varies. Message and data rates may apply. Consent to receive text messages is not a condition of purchasing services.',
      'You may opt out at any time by replying STOP. After an opt-out request, LODEX may send a final confirmation that messaging has stopped. Reply HELP for assistance. Wireless carriers are not responsible for delayed or undelivered messages. Your use of SMS messaging is also subject to the LODEX Privacy Policy.',
    ],
  },
}

export function smsComplianceForPath(pathname = '') {
  const normalized = String(pathname || '/').replace(/\/+$/, '') || '/'
  return SMS_COMPLIANCE[normalized] || null
}

export function installSmsCompliance(documentRef, pathname = '') {
  const disclosure = smsComplianceForPath(pathname)
  if (!disclosure || !documentRef) return false
  if (documentRef.querySelector('[data-sms-compliance]')) return true

  const legalContent = documentRef.querySelector('.legal-content')
  if (!legalContent) return false

  const section = documentRef.createElement('section')
  section.dataset.smsCompliance = ''

  const heading = documentRef.createElement('h2')
  heading.textContent = disclosure.title
  section.appendChild(heading)

  for (const text of disclosure.paragraphs) {
    const paragraph = documentRef.createElement('p')
    paragraph.textContent = text
    section.appendChild(paragraph)
  }

  const updated = documentRef.createElement('p')
  updated.textContent = `SMS terms last updated ${SMS_COMPLIANCE_EFFECTIVE_DATE}.`
  section.appendChild(updated)

  const contactSection = [...legalContent.querySelectorAll(':scope > section')]
    .find(candidate => candidate.querySelector('h2')?.textContent?.trim() === 'Contact LODEX')

  if (contactSection) legalContent.insertBefore(section, contactSection)
  else legalContent.appendChild(section)
  return true
}
