import { expect, test } from '@playwright/test'

import { readFixture } from './fixture'
import { loginAsUnderwriter } from './helpers'

test('an underwriter can accept the recommended decision and see it recorded', async ({ page }) => {
  const fixture = readFixture()
  await loginAsUnderwriter(page, fixture.underwriter_email, fixture.underwriter_password)
  await page.goto(`/app/cases/${fixture.case_id}`)

  await page.getByRole('button', { name: /refer \(recommended\)/i }).click()
  await page.getByRole('button', { name: /confirm refer/i }).click()

  await expect(page.getByText('Referred', { exact: true })).toBeVisible()
  await expect(page.getByText(/underwriter decision: referred/i)).toBeVisible()
})
