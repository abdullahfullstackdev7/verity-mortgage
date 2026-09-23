import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import path from 'node:path'

export interface SeedFixture {
  underwriter_email: string
  underwriter_password: string
  case_id: string
  applicant_name: string
}

export const FIXTURE_PATH = path.resolve(import.meta.dirname, '.fixture.json')

export default function globalSetup() {
  const repoRoot = path.resolve(import.meta.dirname, '..', '..')
  const output = execFileSync('uv', ['run', 'python', '-m', 'scripts.e2e_seed'], {
    cwd: repoRoot,
    encoding: 'utf-8',
    env: { ...process.env, PYTHONUTF8: '1' },
  })

  const jsonLine = output.trim().split('\n').at(-1) ?? '{}'
  const fixture: SeedFixture = JSON.parse(jsonLine)
  writeFileSync(FIXTURE_PATH, JSON.stringify(fixture, null, 2))
}
