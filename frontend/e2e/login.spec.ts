import { expect, test } from '@playwright/test'

import { readFixture } from './fixture'

test('an underwriter can sign in and reach the case queue', async ({ page }) => {
  const { underwriter_email, underwriter_password } = readFixture()

  await page.goto('/login')
  await page.getByLabel(/work email/i).fill(underwriter_email)
  await page.getByLabel(/password/i).fill(underwriter_password)
  await page.getByRole('button', { name: /sign in/i }).click()

  await expect(page).toHaveURL(/\/app\/cases/)
})

test('an incorrect password shows an inline error and does not navigate away', async ({ page }) => {
  const { underwriter_email } = readFixture()

  await page.goto('/login')
  await page.getByLabel(/work email/i).fill(underwriter_email)
  await page.getByLabel(/password/i).fill('definitely-the-wrong-password')
  await page.getByRole('button', { name: /sign in/i }).click()

  await expect(page.getByRole('alert')).toHaveText(/incorrect email or password/i)
  await expect(page).toHaveURL(/\/login/)
})
