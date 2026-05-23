import { afterEach, describe, expect, it, vi } from 'vitest'

describe('agenthub api client base urls', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('normalizes a frontend origin into the proxied /api base url', async () => {
    vi.stubEnv('VITE_HTTP_URL', 'http://localhost:5173')

    const mod = await import('./client')

    expect(mod.API_BASE_URL).toBe('http://localhost:5173/api')
  })

  it('normalizes a frontend ws origin into the proxied /ws base url', async () => {
    vi.stubEnv('VITE_WS_URL', 'ws://localhost:5173')

    const mod = await import('./client')

    expect(mod.WS_BASE_URL).toBe('ws://localhost:5173/ws')
  })
})
