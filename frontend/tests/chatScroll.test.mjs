import assert from 'node:assert/strict'
import { scrollConversationToEnd } from '../src/chatScroll.mjs'

assert.equal(scrollConversationToEnd(null), false)

const container = { scrollHeight: 640, scrollTop: 0 }
assert.equal(scrollConversationToEnd(container), true)
assert.equal(container.scrollTop, 640)

const invalid = { scrollHeight: Number.NaN, scrollTop: 12 }
assert.equal(scrollConversationToEnd(invalid), false)
assert.equal(invalid.scrollTop, 12)

console.log('chat scroll regression checks passed')
