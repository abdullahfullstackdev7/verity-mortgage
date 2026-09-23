import { expect, test } from '@playwright/test'

import { readFixture } from './fixture'
import { loginAsUnderwriter } from './helpers'

test('an underwriter can open a case from the queue and see its flagged discrepancy', async ({ page }) => {
  const fixture = readFixture()
  await loginAsUnderwriter(page, fixture.underwriter_email, fixture.underwriter_password)

  await page.getByText(fixture.applicant_name).click()
  await expect(page).toHaveURL(new RegExp(`/app/cases/${fixture.case_id}`))

  await expect(page.getByRole('heading', { name: fixture.applicant_name })).toBeVisible()
  await expect(page.getByText('Income (Pay Stub)')).toBeVisible()
  await expect(page.getByText('92000.00')).toBeVisible()
  await expect(page.getByText('70000.06')).toBeVisible()
})

test('navigating directly to the case URL shows the same case detail', async ({ page }) => {
  const fixture = readFixture()
  await loginAsUnderwriter(page, fixture.underwriter_email, fixture.underwriter_password)

  await page.goto(`/app/cases/${fixture.case_id}`)
  await expect(page.getByRole('heading', { name: fixture.applicant_name })).toBeVisible()
  await expect(page.getByText(/underwriter decision/i)).toBeVisible()
})
