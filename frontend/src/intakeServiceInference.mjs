export function inferIntakeServiceCategory(payload) {
  if (String(payload?.service_category || '').trim()) return ''

  const userTurns = Array.isArray(payload?.conversation)
    ? payload.conversation
        .filter(turn => turn?.role === 'user')
        .map(turn => turn?.text || '')
        .join(' ')
    : ''
  const text = [payload?.message, payload?.project_summary, userTurns]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  const repairCue = /\b(?:repair(?:s|ed|ing)?|broken|loose|handyman|maintenance|leak(?:s|ed|ing)?|stuck|jammed)\b|\bfix(?:\s*it|es|ed|ing)?\b/i
  if (repairCue.test(text)) return 'Handyman & Property Maintenance'

  return ''
}

export function withInferredIntakeService(payload) {
  const inferredService = inferIntakeServiceCategory(payload)
  return inferredService ? { ...payload, service_category: inferredService } : payload
}
