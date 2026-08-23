import assert from 'node:assert/strict'
import { applyQualificationProgressFloor, guardIntakeReply, normalizeQuestion } from '../src/intakeQuestionGuard.mjs'

const repeatedOutcome = 'What would you like LODEX to accomplish?'
const secondAttempt = guardIntakeReply(
  {
    conversation: [
      { role: 'user', text: 'There is a Sephora store in Crocker Park. Their drawer is broken and comes loose.' },
      { role: 'assistant', text: repeatedOutcome, kind: 'required' },
      { role: 'user', text: 'Repair it' },
    ],
  },
  {
    reply: repeatedOutcome,
    ready_to_schedule: false,
    question_kind: 'required',
  },
)

assert.notEqual(normalizeQuestion(secondAttempt.reply), normalizeQuestion(repeatedOutcome))
assert.equal(secondAttempt.ready_to_schedule, false)
assert.equal(secondAttempt.question_kind, 'extra')
assert.ok(secondAttempt.reply.includes('?'))

const thirdAttempt = guardIntakeReply(
  {
    conversation: [
      { role: 'user', text: 'There is a Sephora store in Crocker Park. Their drawer is broken and comes loose.' },
      { role: 'assistant', text: repeatedOutcome, kind: 'required' },
      { role: 'user', text: 'Repair it' },
      { role: 'assistant', text: secondAttempt.reply, kind: 'extra' },
      { role: 'user', text: 'Fix it tomorrow at 7:30am' },
    ],
  },
  {
    reply: repeatedOutcome,
    ready_to_schedule: false,
    question_kind: 'required',
  },
)

assert.equal(thirdAttempt.ready_to_schedule, false)
assert.equal(thirdAttempt.question_kind, 'extra')
assert.ok(thirdAttempt.reply.includes('?'))
assert.notEqual(normalizeQuestion(thirdAttempt.reply), normalizeQuestion(repeatedOutcome))

const sufficientlyQualifiedRepeat = guardIntakeReply(
  {
    conversation: [
      { role: 'assistant', text: repeatedOutcome, kind: 'required' },
      { role: 'user', text: 'Repair the drawer.' },
      { role: 'assistant', text: 'Which parts of the project should definitely be included in this visit?', kind: 'extra' },
      { role: 'user', text: 'Just the drawer.' },
      { role: 'assistant', text: 'Is there anything about access, height, utilities, tenants, or safety that we should plan around?', kind: 'extra' },
      { role: 'user', text: 'Store is open and first floor.' },
      { role: 'assistant', text: 'What timing are you aiming for—ASAP, a specific day, or flexible?', kind: 'extra' },
      { role: 'user', text: 'Tomorrow morning.' },
    ],
  },
  {
    reply: repeatedOutcome,
    ready_to_schedule: false,
    question_kind: 'required',
  },
)
assert.equal(sufficientlyQualifiedRepeat.ready_to_schedule, true)
assert.equal(sufficientlyQualifiedRepeat.question_kind, 'handoff')
assert.ok(!sufficientlyQualifiedRepeat.reply.includes('?'))
assert.match(sufficientlyQualifiedRepeat.reply, /repeat yourself/i)

const accessVariant = guardIntakeReply(
  {
    conversation: [
      {
        role: 'assistant',
        text: 'What should we know about stairs, doors, parking, elevators, or other delivery access?',
        kind: 'required',
      },
      { role: 'user', text: 'Nothing, first floor.' },
    ],
  },
  {
    reply: 'Are there any access constraints such as stairs or parking?',
    ready_to_schedule: false,
    question_kind: 'required',
  },
)

assert.notEqual(accessVariant.reply, 'Are there any access constraints such as stairs or parking?')
assert.ok(accessVariant.reply.includes('?'))

const distinctQuestion = guardIntakeReply(
  {
    conversation: [
      { role: 'assistant', text: 'Where is the issue?', kind: 'required' },
      { role: 'user', text: 'Kitchen.' },
    ],
  },
  {
    reply: 'When would you like it done?',
    ready_to_schedule: false,
    question_kind: 'required',
  },
)

assert.equal(distinctQuestion.reply, 'When would you like it done?')

const genericQuestion = 'What important detail have we not captured yet that would help us prepare for the visit?'
const concreteConversation = [
  { role: 'user', text: 'CONCRETE' },
  { role: 'assistant', text: 'What should we find or furnish first?', kind: 'required' },
  { role: 'user', text: 'CONCRETE SLAB' },
  { role: 'assistant', text: genericQuestion, kind: 'extra' },
  { role: 'user', text: 'IDK' },
]

const declinedDetail = guardIntakeReply(
  { message: 'IDK', conversation: concreteConversation },
  { reply: genericQuestion, ready_to_schedule: false, question_kind: 'extra' },
)
assert.equal(declinedDetail.ready_to_schedule, true)
assert.equal(declinedDetail.question_kind, 'handoff')
assert.ok(!declinedDetail.reply.includes('?'))

const exactGenericRepeat = guardIntakeReply(
  {
    message: 'something',
    conversation: [
      ...concreteConversation.slice(0, -1),
      { role: 'user', text: 'something' },
    ],
  },
  { reply: genericQuestion, ready_to_schedule: false, question_kind: 'extra' },
)
assert.equal(exactGenericRepeat.ready_to_schedule, false)
assert.equal(exactGenericRepeat.question_kind, 'extra')
assert.ok(exactGenericRepeat.reply.includes('?'))
assert.notEqual(normalizeQuestion(exactGenericRepeat.reply), normalizeQuestion(genericQuestion))

const frustratedCustomer = guardIntakeReply(
  {
    message: 'YOU ASKING ME THE SAME QUESTION AGAIN?!',
    conversation: [
      ...concreteConversation.slice(0, -1),
      { role: 'user', text: 'YOU ASKING ME THE SAME QUESTION AGAIN?!' },
    ],
  },
  { reply: genericQuestion, ready_to_schedule: false, question_kind: 'extra' },
)
assert.equal(frustratedCustomer.ready_to_schedule, true)
assert.equal(frustratedCustomer.question_kind, 'handoff')
assert.ok(!frustratedCustomer.reply.includes('?'))

const frozenQualification = {
  reply: 'What timing are you aiming for?',
  ready_to_schedule: false,
  question_kind: 'required',
  qualification: {
    progress: 0,
    qualified: false,
    requirements: [
      { id: 'scope', covered: false },
      { id: 'access', covered: false },
      { id: 'timing', covered: false },
      { id: 'priority', covered: false },
    ],
  },
}
const shedConversation = [
  { role: 'user', text: 'I would like to build a shed behind my business.' },
  { role: 'assistant', text: 'Roughly what size or dimensions are we working with?', kind: 'required' },
  { role: 'user', text: 'About 12 by 16 feet.' },
  { role: 'assistant', text: 'Is access straightforward, or is there anything onsite we should plan around?', kind: 'required' },
  { role: 'user', text: 'Back lot is open and easy to reach.' },
]
const recoveredQualification = applyQualificationProgressFloor(frozenQualification, shedConversation)
assert.equal(recoveredQualification.qualification.progress, 50)

const realServerProgress = applyQualificationProgressFloor(
  { ...frozenQualification, qualification: { ...frozenQualification.qualification, progress: 25 } },
  shedConversation,
)
assert.equal(realServerProgress.qualification.progress, 25)

console.log('intake question repetition guard checks passed')
