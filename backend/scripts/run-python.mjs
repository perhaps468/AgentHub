import { existsSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { join } from 'node:path'

const args = process.argv.slice(2)
const candidates = [
  process.env.PYTHON,
  process.env.USERPROFILE
    ? join(
        process.env.USERPROFILE,
        '.cache',
        'codex-runtimes',
        'codex-primary-runtime',
        'dependencies',
        'python',
        'python.exe',
      )
    : undefined,
  'python',
  'py',
].filter(Boolean)

for (const candidate of candidates) {
  if (candidate.endsWith('.exe') && !existsSync(candidate)) {
    continue
  }

  const result = spawnSync(candidate, args, {
    stdio: 'inherit',
    shell: false,
  })

  if (!result.error) {
    process.exit(result.status ?? 0)
  }

  if (result.error.code !== 'ENOENT') {
    console.error(result.error.message)
    process.exit(1)
  }
}

console.error('Python was not found. Set PYTHON or install Python 3.12+.')
process.exit(1)
