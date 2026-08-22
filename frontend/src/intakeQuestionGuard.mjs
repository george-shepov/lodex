const QUESTION_TOPICS = [
  ['outcome', /\b(?:accomplish|outcome|successful result|finished|done|repair|fix|changed?)\b/i],
  ['access', /\b(?:access|stairs?|doors?|parking|elevators?|loading|height|utility|utilities|tenant|safety)\b/i],
  ['timing', /\b(?:when|timing|deadline|ready|schedule|day|date|asap|tomorrow|week)\b/i],
  ['quantity', /\b(?:how many|quantity|several|number of|items?|rooms?|areas?|spaces?)\b/i],
  ['location', /\b(?:where|location|which room|which area|onsite|site)\b/i],
  ['size', /\b(?:size|large|dimensions?|measurements?|square feet|sq\.?\s*ft)\b/i],
  ['budget', /\b(?:budget|spend|spending|cost cap|price range|maximum|minimum spend)\b/i],
  ['finish', /\b(?:finish|material|color|appearance|preserve|match)\b/i],
  ['fulfillment', /\b(?:pickup|pick up|delivery|deliver|setup|assemble|assembly|install)\b/i],
  ['scope', /\b(?:scope|which parts?|included|involved|attention)\b/i],
]

const MIN_QUALIFYING_QUESTIONS = 3

export function normalizeQuestion(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

export function questionTopic(text) {
  const value = String(text || '')
  const match = QUESTION_TOPICS.find(([, pattern]) => pattern.test(value))
  return match?.[0] || ''
}

export function rephraseRepeatedQuestion(text, topic = questionTopic(text)) {
  const variants = {
    outcome: 'What should be different when the job is finished?',
    access: 'Is access straightforward, or is there anything onsite we should plan around?',
    timing: 'What timing are you aiming for—ASAP, a specific day, or flexible?',
    quantity: 'About how many items, rooms, or areas are involved?',
    location: 'Which room, area, or specific item should we plan to work on?',
    size: 'Roughly what size or dimensions are we working with?',
    budget: 'Should we work to a spending cap, or optimize for the lowest practical cost?',
    finish: 'Is there a finish, material, or appearance we need to preserve or match?',
    fulfillment: 'Should LODEX handle pickup, delivery, setup, or all of it?',
    scope: 'Which parts of the project should be included in this visit?',
  }
  return variants[topic] || 'What important detail have we not captured yet that would help us prepare for the visit?'
}

export function customerWantsHandoff(text, previousQuestion = null) {
  const value = String(text || '').trim()
  if (/\b(?:same question|asking me the same|asked me already|how many times|stop asking|stop confirming)\b/i.test(value)) return true
  if (/^(?:that['’]?s\s+all|no\s+more(?:\s+details?)?|nothing\s+else)[\s.!?]*$/i.test(value)) return true
  if (!/^(?:i\s*(?:do\s*n['’]?t|don['’]?t)\s*know|idk|not\s+sure|nothing)[\s.!?]*$/i.test(value)) return false

  const priorText = String(previousQuestion?.text || '')
  return previousQuestion?.kind === 'extra'
    || /\b(?:important detail|anything else)\b/i.test(priorText)
}

function usefulUnusedQuestion(conversation) {
  const transcript = conversation.map(turn => String(turn?.text || '')).join(' ')
  const askedTopics = new Set(
    conversation
      .filter(turn => turn?.role === 'assistant' && String(turn?.text || '').includes('?'))
      .map(turn => questionTopic(turn.text))
      .filter(Boolean),
  )

  const candidates = [
    ['scope', 'Which parts of the project should definitely be included in this visit?'],
    ['quantity', 'About how many items, rooms, or areas are involved altogether?'],
    ['access', 'Is there anything about access, height, utilities, tenants, or safety that we should plan around?'],
    ['finish', 'Are there any materials, finishes, colors, or existing details we need to preserve or match?'],
    ['timing', 'What timing are you aiming for—ASAP, a specific day, or flexible?'],
    ['budget', 'Is there a spending target or priority we should keep in mind while planning the work?'],
  ]

  for (const [topic, question] of candidates) {
    if (askedTopics.has(topic)) continue
    const topicPattern = QUESTION_TOPICS.find(([name]) => name === topic)?.[1]
    if (topicPattern && topicPattern.test(transcript)) continue
    return question
  }

  return 'Before we schedule, is there one more detail about the work, access, materials, or timing that would help us arrive better prepared?'
}

export function guardIntakeReply(requestPayload, responsePayload) {
  if (!responsePayload) return responsePayload

  const conversation = Array.isArray(requestPayload?.conversation) ? requestPayload.conversation : []
  const latestCustomerMessage = [...conversation].reverse().find(turn => turn?.role === 'user')?.text
    || requestPayload?.message
  const previousQuestion = [...conversation].reverse().find(turn => turn?.role === 'assistant' && String(turn?.text || '').includes('?'))
  const priorQuestions = conversation.length
    ? conversation
        .filter(turn => turn?.role === 'assistant' && String(turn?.text || '').includes('?'))
        .map(turn => String(turn.text).trim())
    : []

  if (
    responsePayload.ready_to_schedule
    && responsePayload.question_kind === 'handoff'
    && priorQuestions.length < MIN_QUALIFYING_QUESTIONS
    && !customerWantsHandoff(latestCustomerMessage, previousQuestion)
  ) {
    return {
      ...responsePayload,
      reply: usefulUnusedQuestion(conversation),
      ready_to_schedule: false,
      question_kind: 'extra',
    }
  }

  if (!['required', 'extra'].includes(responsePayload.question_kind)) {
    return responsePayload
  }

  const reply = String(responsePayload.reply || '').trim()
  if (!reply.includes('?')) return responsePayload

  if (customerWantsHandoff(latestCustomerMessage, previousQuestion)) {
    return {
      ...responsePayload,
      reply: "That's enough to prepare for a first visit. Choose a preferred visit window below, and we can verify the remaining details onsite.",
      ready_to_schedule: true,
      question_kind: 'handoff',
    }
  }

  if (!priorQuestions.length) return responsePayload

  const normalized = normalizeQuestion(reply)
  const topic = questionTopic(reply)
  const exactPrior = priorQuestions.filter(question => normalizeQuestion(question) === normalized).length
  const sameTopicPrior = topic
    ? priorQuestions.filter(question => questionTopic(question) === topic).length
    : 0

  if (exactPrior >= 1 || (topic && sameTopicPrior >= 2)) {
    return {
      ...responsePayload,
      reply: "I won't make you repeat yourself. We can verify that detail during the visit—choose a preferred visit window below.",
      ready_to_schedule: true,
      question_kind: 'handoff',
    }
  }

  if (topic && sameTopicPrior >= 1) {
    let rephrased = rephraseRepeatedQuestion(reply, topic)
    if (normalizeQuestion(rephrased) === normalized) {
      return {
        ...responsePayload,
        reply: "I won't make you repeat yourself. We can verify that detail during the visit—choose a preferred visit window below.",
        ready_to_schedule: true,
        question_kind: 'handoff',
      }
    }
    return {
      ...responsePayload,
      reply: rephrased,
    }
  }

  return responsePayload
}
