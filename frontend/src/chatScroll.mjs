export function scrollConversationToEnd(container) {
  if (!container) return false

  const scrollHeight = Number(container.scrollHeight)
  if (!Number.isFinite(scrollHeight)) return false

  // Instant positioning avoids stacking compositor-driven smooth-scroll
  // animations while rapid chat DOM updates are still settling.
  container.scrollTop = scrollHeight
  return true
}
