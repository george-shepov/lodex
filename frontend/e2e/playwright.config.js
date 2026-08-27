import { defineConfig, devices } from '@playwright/test'

const liveDemo = process.env.LODEX_DEMO_LIVE === '1'
const targetUrl = process.env.LODEX_DEMO_URL || 'http://127.0.0.1:4173'

export default defineConfig({
  testDir: './tests',
  outputDir: './artifacts',
  timeout: 45_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['line'], ['html', { outputFolder: 'report', open: 'never' }]] : 'line',
  use: {
    baseURL: targetUrl,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: liveDemo ? undefined : {
    command: 'npm run dev -- --host 127.0.0.1 --port 4173',
    cwd: '..',
    url: targetUrl,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    {
      name: 'chromium',
      grepInvert: /@demo/,
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
        video: 'retain-on-failure',
      },
    },
    {
      name: 'demo',
      grep: /@demo/,
      use: {
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
        video: { mode: 'on', size: { width: 1920, height: 1080 } },
        colorScheme: 'light',
      },
    },
  ],
})
