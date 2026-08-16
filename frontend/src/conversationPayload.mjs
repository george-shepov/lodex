export function serializeConversation(messages = [], limit = 24) {
  return messages.slice(-limit).map(item => ({
    role: item.role,
    text: item.text,
    ...(item.kind ? { kind: item.kind } : {}),
  }))
}
