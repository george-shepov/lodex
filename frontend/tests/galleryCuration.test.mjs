import assert from 'node:assert/strict'
import { applyGalleryCuration, hiddenGalleryProjectIds } from '../src/galleryCuration.mjs'

const projects = [
  { id: 'lz-125', title: 'Installation inspiration 02' },
  { id: 'lz-149', title: 'Installation inspiration 03' },
  { id: 'lz-151', title: 'Installation inspiration 04' },
  { id: 'lz-150', title: 'Installation inspiration 05' },
  { id: 'lz-152', title: 'Installation inspiration 06' },
]

const curated = applyGalleryCuration(projects)

assert.deepEqual([...hiddenGalleryProjectIds], ['lz-125', 'lz-149', 'lz-150', 'lz-152'])
assert.deepEqual(curated.map(project => project.id), ['lz-151'])
assert.equal(curated, projects, 'curation should preserve the shared gallery array reference')

console.log('gallery curation regression checks passed')
