import '@testing-library/jest-dom/vitest'
import { afterEach, beforeEach, vi } from 'vitest'

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString()
      const method = (init?.method || 'GET').toUpperCase()

      if (url.includes('/api/v1/workspaces/active') && method === 'GET') {
        return jsonResponse(null)
      }

      if (url.includes('/api/v1/workspaces/') && url.includes('/questions') && method === 'GET') {
        return jsonResponse([])
      }

      return jsonResponse(
        {
          error: {
            code: 'NOT_IMPLEMENTED_IN_SMOKE',
            message: 'Endpoint not stubbed in smoke setup.',
            details: { url, method },
          },
        },
        404,
      )
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})
