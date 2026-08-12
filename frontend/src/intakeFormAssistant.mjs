export const INTAKE_DRAFT_KEY = 'lodex-intake-draft-v1'

function clean(value) {
  return String(value || '').replace(/\s+/g, ' ').trim().replace(/[.,;:!?]+$/, '')
}

function localIsoDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addDays(date, days) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function formatClock(hourText, minuteText, meridiemText) {
  const hour = Number(hourText)
  const minute = String(minuteText || '00').padStart(2, '0')
  const meridiem = String(meridiemText || '').replace(/\./g, '').toUpperCase()
  return `${hour}:${minute} ${meridiem}`
}

export function conversationSummary(conversation = []) {
  return conversation
    .filter(turn => turn?.role === 'user')
    .map(turn => String(turn?.text || '').trim())
    .filter(Boolean)
    .join('\n')
}

export function inferProjectLocation(text) {
  const value = String(text || '')
  if (!value.trim()) return ''

  const street = value.match(/\b\d{1,6}\s+[A-Za-z0-9.'#-]+(?:\s+[A-Za-z0-9.'#-]+){0,6}\s+(?:st(?:reet)?|rd|road|ave(?:nue)?|blvd|boulevard|dr(?:ive)?|ln|lane|ct|court|way|pkwy|parkway)\b[^\n,;.!?]*/i)
  if (street) {
    return clean(street[0]).split(/\s+(?:and|their|they|it|where|which|that)\b/i)[0].trim()
  }

  const commercial = value.match(/\b((?:[A-Za-z0-9&'.-]+\s+){0,4}(?:store|shop|restaurant|office|building|warehouse|school|clinic|hotel))\s+in\s+([A-Za-z0-9&'.-]+(?:\s+[A-Za-z0-9&'.-]+){0,5})/i)
  if (commercial) {
    const leadingStops = new Set(['there', 'is', 'a', 'an', 'the', 'this', 'that'])
    const trailingStops = new Set(['their', 'they', 'it', 'the', 'that', 'where', 'which', 'has', 'have', 'is', 'are', 'was', 'were', 'drawer', 'door', 'window', 'cabinet', 'broken', 'loose'])
    const left = commercial[1].split(/\s+/).filter(Boolean)
    while (left.length && leadingStops.has(left[0].toLowerCase())) left.shift()
    const right = commercial[2].split(/\s+/).filter(Boolean)
    const stopAt = right.findIndex(word => trailingStops.has(clean(word).toLowerCase()))
    const placeWords = stopAt >= 0 ? right.slice(0, stopAt) : right
    if (left.length && placeWords.length) return clean(`${left.join(' ')} in ${placeWords.join(' ')}`)
  }

  const atPlace = value.match(/\b(?:at|in)\s+([A-Za-z0-9&'.-]+(?:\s+[A-Za-z0-9&'.-]+){0,4})(?=\s+(?:their|they|it|that|where|which|has|have|is|are|was|were)\b|[\n,;.!?]|$)/i)
  return atPlace ? clean(atPlace[1]) : ''
}

export function inferTiming(text, now = new Date()) {
  const value = String(text || '')
  let preferredDate = ''
  let dateLabel = ''

  if (/\btomorrow\b/i.test(value)) {
    preferredDate = localIsoDate(addDays(now, 1))
    dateLabel = 'Tomorrow'
  } else if (/\btoday\b/i.test(value)) {
    preferredDate = localIsoDate(now)
    dateLabel = 'Today'
  } else {
    const isoDate = value.match(/\b(20\d{2}-\d{2}-\d{2})\b/)
    if (isoDate) {
      preferredDate = isoDate[1]
      dateLabel = isoDate[1]
    }
  }

  const clock = value.match(/\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b/i)
  const clockLabel = clock ? formatClock(clock[1], clock[2], clock[3]) : ''

  let preferredTime = ''
  if (clockLabel) preferredTime = `Requested · ${clockLabel}`
  else if (/\blate afternoon\b/i.test(value)) preferredTime = 'Late afternoon · 3 PM–6 PM'
  else if (/\bafternoon\b/i.test(value)) preferredTime = 'Afternoon · 12 PM–3 PM'
  else if (/\bmorning\b/i.test(value)) preferredTime = 'Morning · 9 AM–12 PM'

  let label = ''
  if (dateLabel && clockLabel) label = `${dateLabel} at ${clockLabel}`
  else if (dateLabel) label = dateLabel
  else if (clockLabel) label = clockLabel
  else if (/\basap\b|as soon as (?:possible|practical)/i.test(value)) label = 'As soon as practical'
  else if (preferredTime) label = preferredTime

  return { label, preferredDate, preferredTime }
}

export function buildIntakeDraft({ conversation = [], serviceCategory = '', capturedAddress = '', existing = {}, now = new Date() } = {}) {
  const chatSummary = conversationSummary(conversation)
  const sourceText = chatSummary || String(existing.summary || '')
  const timing = inferTiming(sourceText, now)
  const selectedService = clean(serviceCategory)
  const usableService = selectedService && !/^(?:your project|general inquiry)$/i.test(selectedService) ? selectedService : ''

  return {
    ...existing,
    service: usableService || existing.service || '',
    summary: existing.summaryEdited ? existing.summary || '' : chatSummary || existing.summary || '',
    location: existing.locationEdited
      ? existing.location || ''
      : existing.location || clean(capturedAddress) || inferProjectLocation(sourceText),
    timing: existing.timingEdited ? existing.timing || '' : existing.timing || timing.label,
    preferredDate: existing.preferredDate || timing.preferredDate,
    preferredTime: existing.preferredTime || timing.preferredTime,
  }
}

export function appointmentPayloadFromDraft(payload, draft = {}) {
  const next = { ...payload }
  if (draft.summary) next.project_summary = draft.summary
  if (draft.service && (!next.service_category || /^general inquiry$/i.test(next.service_category))) next.service_category = draft.service
  if (draft.location) next.address = draft.location
  if (draft.preferredDate) next.preferred_date = draft.preferredDate
  if (draft.preferredTime) next.preferred_time = draft.preferredTime
  if (typeof draft.confirmed === 'boolean') next.assumptions_confirmed = draft.confirmed
  return next
}
