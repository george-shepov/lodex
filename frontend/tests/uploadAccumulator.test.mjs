import assert from 'node:assert/strict'
import { createUploadAccumulator, mergeProjectUploads } from '../src/uploadAccumulator.mjs'

class MemoryStorage {
  constructor() { this.values = new Map() }
  getItem(key) { return this.values.has(key) ? this.values.get(key) : null }
  setItem(key, value) { this.values.set(key, String(value)) }
  removeItem(key) { this.values.delete(key) }
}

const storage = new MemoryStorage()
const accumulator = createUploadAccumulator(storage)
accumulator.remember({ upload_id: 'one', filename: 'kitchen.jpg', media_type: 'image/jpeg', description: 'Kitchen' })
accumulator.remember({ upload_id: 'two', filename: 'bath.jpg', media_type: 'image/jpeg', description: 'Bathroom' })

const enriched = accumulator.enrich({
  name: 'Customer',
  uploads: [{ upload_id: 'two', filename: 'bath.jpg', media_type: 'image/jpeg', description: 'Bathroom close-up' }],
})
assert.deepEqual(enriched.uploads.map(file => file.upload_id), ['one', 'two'])
assert.equal(enriched.uploads[1].description, 'Bathroom close-up')

const restored = createUploadAccumulator(storage)
assert.deepEqual(restored.list().map(file => file.upload_id), ['one', 'two'])

assert.deepEqual(
  mergeProjectUploads([{ upload_id: 'same', filename: 'new.jpg' }], [{ upload_id: 'same', filename: 'old.jpg' }]),
  [{ upload_id: 'same', filename: 'new.jpg', media_type: 'application/octet-stream', description: '' }],
)

restored.clear()
assert.equal(storage.getItem('lodex-pending-uploads-v1'), null)
assert.deepEqual(restored.list(), [])

console.log('upload accumulator regression checks passed')
