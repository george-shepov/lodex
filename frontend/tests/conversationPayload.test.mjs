import assert from 'node:assert/strict'
import { serializeConversation } from '../src/conversationPayload.mjs'

assert.deepEqual(
  serializeConversation([
    { role: 'user', text: 'The kitchen needs work.', localOnly: true },
    { role: 'assistant', text: 'When should we start?', kind: 'required' },
  ]),
  [
    { role: 'user', text: 'The kitchen needs work.' },
    { role: 'assistant', text: 'When should we start?', kind: 'required' },
  ],
)

assert.deepEqual(
  serializeConversation([
    { role: 'user', text: 'one' },
    { role: 'user', text: 'two' },
  ], 1),
  [{ role: 'user', text: 'two' }],
)

console.log('conversation payload regression checks passed')
