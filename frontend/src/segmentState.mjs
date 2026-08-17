export const CUSTOMER_SEGMENT_KEY = 'lodex-customer-segment-v1'
export const HOME_PROJECT_SIZE_KEY = 'lodex-home-project-size-v1'

export const SEGMENT_LABELS = {
  home: 'LODEX Home',
  business: 'LODEX Business',
  enterprise: 'LODEX Enterprise',
}

export function readStoredSegment(storage = globalThis?.localStorage) {
  try {
    const value = storage?.getItem(CUSTOMER_SEGMENT_KEY) || ''
    return SEGMENT_LABELS[value] ? value : ''
  } catch {
    return ''
  }
}

export function readStoredHomeProjectSize(storage = globalThis?.localStorage) {
  try {
    const value = storage?.getItem(HOME_PROJECT_SIZE_KEY) || ''
    return ['small', 'several', 'major'].includes(value) ? value : ''
  } catch {
    return ''
  }
}

export function segmentIntakeState(storage = globalThis?.localStorage) {
  const customerSegment = readStoredSegment(storage)
  if (!customerSegment) return {}
  return {
    customer_segment: customerSegment,
    customer_type: customerSegment === 'home' ? 'homeowner' : customerSegment,
    ...(customerSegment === 'home'
      ? { project_size_class: readStoredHomeProjectSize(storage) || null }
      : { project_size_class: null }),
  }
}

export function withCustomerSegment(payload, storage = globalThis?.localStorage) {
  if (!payload || typeof payload !== 'object') return payload
  const state = segmentIntakeState(storage)
  if (!state.customer_segment) return payload
  const label = SEGMENT_LABELS[state.customer_segment]
  const category = String(payload.service_category || '').trim()
  const baseCategory = category.replace(/^LODEX\s+(?:Home|Business|Enterprise)\s*·\s*/i, '').trim()
  return {
    ...payload,
    ...state,
    service_category: `${label} · ${baseCategory || 'General inquiry'}`,
  }
}
