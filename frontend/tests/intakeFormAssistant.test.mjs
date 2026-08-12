import assert from 'node:assert/strict'
import { appointmentPayloadFromDraft, buildIntakeDraft, inferProjectLocation, inferTiming } from '../src/intakeFormAssistant.mjs'

const fixedNow = new Date(2026, 7, 12, 12, 0, 0)

assert.equal(
  inferProjectLocation('Sue there is a Sephora store in Crocker Park Their drawer is broken it comes loose'),
  'Sephora store in Crocker Park',
)

assert.equal(
  inferProjectLocation('The job is at 5160 Stevenson St and the kitchen needs attention.'),
  '5160 Stevenson St',
)

const timing = inferTiming('Fix it tomorrow at 7:30am', fixedNow)
assert.deepEqual(timing, {
  label: 'Tomorrow at 7:30 AM',
  preferredDate: '2026-08-13',
  preferredTime: 'Requested · 7:30 AM',
})

const draft = buildIntakeDraft({
  now: fixedNow,
  serviceCategory: 'Handyman & Property Maintenance',
  conversation: [
    { role: 'user', text: 'There is a Sephora store in Crocker Park. Their drawer is broken and comes loose.' },
    { role: 'assistant', text: 'When should we handle it?' },
    { role: 'user', text: 'Tomorrow at 7:30am.' },
  ],
})
assert.equal(draft.service, 'Handyman & Property Maintenance')
assert.match(draft.summary, /drawer is broken/i)
assert.equal(draft.location, 'Sephora store in Crocker Park')
assert.equal(draft.timing, 'Tomorrow at 7:30 AM')
assert.equal(draft.preferredDate, '2026-08-13')
assert.equal(draft.preferredTime, 'Requested · 7:30 AM')

const edited = buildIntakeDraft({
  now: fixedNow,
  conversation: [{ role: 'user', text: 'Replace the door tomorrow.' }],
  existing: {
    summary: 'Repair the existing door instead of replacing it.',
    summaryEdited: true,
    location: 'Customer will provide location',
    locationEdited: true,
  },
})
assert.equal(edited.summary, 'Repair the existing door instead of replacing it.')
assert.equal(edited.location, 'Customer will provide location')

assert.deepEqual(
  appointmentPayloadFromDraft(
    {
      project_summary: 'chat summary',
      service_category: 'General inquiry',
      address: 'old',
      preferred_date: '',
      preferred_time: '',
      assumptions_confirmed: false,
    },
    {
      summary: 'Reviewed summary',
      service: 'Handyman & Property Maintenance',
      location: 'Sephora store in Crocker Park',
      preferredDate: '2026-08-13',
      preferredTime: 'Requested · 7:30 AM',
      confirmed: true,
    },
  ),
  {
    project_summary: 'Reviewed summary',
    service_category: 'Handyman & Property Maintenance',
    address: 'Sephora store in Crocker Park',
    preferred_date: '2026-08-13',
    preferred_time: 'Requested · 7:30 AM',
    assumptions_confirmed: true,
  },
)

console.log('intake form assistant regression checks passed')
