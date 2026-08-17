import assert from 'node:assert/strict'
import { segmentIntakeState, withCustomerSegment } from '../src/segmentState.mjs'

function storage(values) {
  return { getItem: key => values[key] || null }
}

const homeStorage = storage({
  'lodex-customer-segment-v1': 'home',
  'lodex-home-project-size-v1': 'small',
})
assert.deepEqual(segmentIntakeState(homeStorage), {
  customer_segment: 'home',
  customer_type: 'homeowner',
  project_size_class: 'small',
})
assert.deepEqual(
  withCustomerSegment({ service_category: 'Handyman & Property Maintenance' }, homeStorage),
  {
    customer_segment: 'home',
    customer_type: 'homeowner',
    project_size_class: 'small',
    service_category: 'LODEX Home · Handyman & Property Maintenance',
  },
)

const business = segmentIntakeState(storage({ 'lodex-customer-segment-v1': 'business' }))
assert.equal(business.customer_segment, 'business')
assert.equal(business.customer_type, 'business')
assert.equal(business.project_size_class, null)

const enterprise = withCustomerSegment(
  { service_category: 'LODEX Home · General inquiry' },
  storage({ 'lodex-customer-segment-v1': 'enterprise' }),
)
assert.equal(enterprise.service_category, 'LODEX Enterprise · General inquiry')
assert.equal(enterprise.customer_segment, 'enterprise')

console.log('segment state checks passed')
