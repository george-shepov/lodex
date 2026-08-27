import { expect, test } from '@playwright/test'

const requirements = [
  { id: 'scope', label: 'Project scope', covered: false },
  { id: 'access', label: 'Site access', covered: false },
  { id: 'timing', label: 'Timing', covered: false },
  { id: 'priority', label: 'Priority', covered: false },
]

const replies = [
  'Roughly what size or dimensions are we working with?',
  'Is access straightforward, or is there anything onsite we should plan around?',
  'What timing are you aiming for—ASAP, a specific day, or flexible?',
]

async function mockFrozenQualification(page) {
  let responseIndex = 0
  await page.route('**/api/intake/chat', async route => {
    const reply = replies[Math.min(responseIndex, replies.length - 1)]
    responseIndex += 1
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        reply,
        ready_to_schedule: false,
        question_kind: 'required',
        qualification: {
          progress: 0,
          qualified: false,
          label: 'Project details',
          requirements,
        },
      }),
    })
  })
}

async function openIntake(page, { live = false } = {}) {
  if (!live) await mockFrozenQualification(page)
  await page.goto('/#intake')
  await page.locator('#intake').scrollIntoViewIfNeeded()
  await expect(page.locator('.scope-meter-top b')).toHaveText('0%')
}

async function answer(page, text) {
  const composer = page.locator('.composer textarea')
  await composer.fill(text)
  await page.locator('.composer button[type="submit"]').click()
  await expect(page.locator('.composer .typing')).toBeHidden()
}

test('confidence advances for distinct answered questions while API remains frozen at zero', async ({ page }) => {
  await openIntake(page)

  await answer(page, 'I need a 12 by 16 foot shed behind my business.')
  await expect(page.locator('.scope-meter-top b')).toHaveText('0%')

  await answer(page, 'The shed should be about 12 by 16 feet.')
  await expect(page.locator('.scope-meter-top b')).toHaveText('25%')

  await answer(page, 'The back lot is open and easy to reach.')
  await expect(page.locator('.scope-meter-top b')).toHaveText('50%')
})

test('@demo records the LODEX confidence story', async ({ page }) => {
  const live = process.env.LODEX_DEMO_LIVE === '1'
  await openIntake(page, { live })
  await page.waitForTimeout(1800)

  await answer(page, 'I need a 12 by 16 foot shed behind my business.')
  await page.waitForTimeout(1800)

  await answer(page, 'The shed should be about 12 by 16 feet with space for tools and equipment.')
  await expect(page.locator('.scope-meter-top b')).not.toHaveText('0%')
  await page.waitForTimeout(2200)

  const before = Number((await page.locator('.scope-meter-top b').innerText()).replace('%', ''))
  await answer(page, 'The back lot is open, level, and easy to reach from the driveway.')
  await expect.poll(async () => Number((await page.locator('.scope-meter-top b').innerText()).replace('%', ''))).toBeGreaterThan(before)
  await page.waitForTimeout(3000)
})
