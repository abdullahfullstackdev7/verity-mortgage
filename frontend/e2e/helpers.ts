import type { Page } from '@playwright/test'

export async function loginAsUnderwriter(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.getByLabel(/work email/i).fill(email)
  await page.getByLabel(/password/i).fill(password)
  await page.getByRole('button', { name: /sign in/i }).click()
  await page.waitForURL(/\/app\/cases/)
}
