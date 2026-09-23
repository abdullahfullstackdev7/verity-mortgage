import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  globalSetup: './e2e/global-setup.ts',
  use: {
    baseURL: 'http://localhost:5183',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      // Dedicated, unusual ports: this machine runs dev servers for several
      // other projects, and reusing a same-numbered server from a different
      // app silently points the E2E suite at the wrong app.
      command: 'npm run dev -- --port 5183 --strictPort',
      url: 'http://localhost:5183',
      reuseExistingServer: false,
      timeout: 60_000,
      env: { VITE_API_BASE_URL: 'http://localhost:8103/api/v1' },
    },
    {
      command: 'uv run uvicorn backend.app.main:app --port 8103',
      cwd: '..',
      url: 'http://localhost:8103/docs',
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
