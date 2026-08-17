import assert from 'node:assert/strict'
import { guardIntakeReply, normalizeQuestion } from '../src/intakeQuestionGuard.mjs'

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
assert.equal(secondAttempt.ready_to_schedule, true)
assert.equal(secondAttempt.question_kind, 'handoff')
assert.ok(!secondAttempt.reply.includes('?'))

const thirdAttempt = guardIntakeReply(
  {
    conversation: [
      { role: 'user', text: 'There is a Sephora store in Crocker Park. Their drawer is broken and comes loose.' },
      { role: 'assistant', text: repeatedOutcome, kind: 'required' },
      { role: 'user', text: 'Repair it' },
      { role: 'assistant', text: secondAttempt.reply, kind: 'required' },
      { role: 'user', text: 'Fix it tomorrow at 7:30am' },
    ],
  },
  {
    reply: repeatedOutcome,
    ready_to_schedule: false,
    question_kind: 'required',
  },
)

assert.equal(thirdAttempt.ready_to_schedule, true)
assert.equal(thirdAttempt.question_kind, 'handoff')
assert.ok(!thirdAttempt.reply.includes('?'))
assert.match(thirdAttempt.reply, /repeat yourself/i)

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
assert.equal(exactGenericRepeat.ready_to_schedule, true)
assert.equal(exactGenericRepeat.question_kind, 'handoff')

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

console.log('intake question repetition guard checks passed')
