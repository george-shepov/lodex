import assert from 'node:assert/strict'
import { inferIntakeServiceCategory, withInferredIntakeService } from '../src/intakeServiceInference.mjs'

const repairService = 'Handyman & Property Maintenance'
const opening = 'Sue there is a Sephora store in Crocker Park Their drover is broken it comes loose'

assert.equal(
  inferIntakeServiceCategory({
    message: opening,
    project_summary: opening,
    service_category: '',
    conversation: [{ role: 'user', text: opening }],
  }),
  repairService,
)
assert.equal(inferIntakeServiceCategory({ message: 'Fixit tomorrow at 7:30am', service_category: '' }), repairService)
assert.equal(inferIntakeServiceCategory({ message: 'Repair it', service_category: '' }), repairService)
assert.equal(
  inferIntakeServiceCategory({ message: 'Repair it', service_category: 'Cleaning & Surface Restoration' }),
  '',
)
assert.equal(inferIntakeServiceCategory({ message: 'I need help with my property', service_category: '' }), '')
assert.equal(
  withInferredIntakeService({ message: 'The drawer is broken and comes loose', service_category: '' }).service_category,
  repairService,
)

console.log('intake service inference regression checks passed')
