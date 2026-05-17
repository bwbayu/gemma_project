export interface ApiErrorEnvelope {
  error?: {
    code?: string
    message?: string
    details?: unknown
  }
}

/** Typed error thrown when an API response has a non-2xx status. Carries the error code, HTTP status, and optional details payload. */
export class ApiError extends Error {
  code: string
  status: number
  details: unknown

  constructor(message: string, status: number, code = 'API_ERROR', details: unknown = null) {
    super(message)
    this.code = code
    this.status = status
    this.details = details
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL?.trim() || 'http://localhost:8001').replace(/\/+$/, '')
const API_PREFIX = '/api/v1'

/** Prepend the base URL and API prefix to a path, normalizing leading slashes. */
function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${API_PREFIX}${normalizedPath}`
}

/** Extract a structured ApiError from a non-OK response, falling back to a generic message. */
async function parseError(response: Response): Promise<ApiError> {
  const payload: ApiErrorEnvelope | null = await response
    .json()
    .then((value) => value as ApiErrorEnvelope)
    .catch(() => null)

  const code = payload?.error?.code || 'API_ERROR'
  const message = payload?.error?.message || `Request failed with status ${response.status}.`
  const details = payload?.error?.details ?? null

  return new ApiError(message, response.status, code, details)
}

/** Central fetch wrapper: builds the URL, sets JSON headers, parses errors, and returns typed response data. */
export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== 'undefined' && init?.body instanceof FormData
  const response = await fetch(buildApiUrl(path), {
    headers: {
      Accept: 'application/json',
      ...(!isFormData && init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
    ...init,
  })

  if (!response.ok) {
    throw await parseError(response)
  }

  if (response.status === 204) {
    return null as T
  }

  return (await response.json()) as T
}
