import { readFileSync } from 'node:fs'

import { FIXTURE_PATH, type SeedFixture } from './global-setup'

export function readFixture(): SeedFixture {
  return JSON.parse(readFileSync(FIXTURE_PATH, 'utf-8'))
}
