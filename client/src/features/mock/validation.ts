const FORM_URL_PATTERN =
  /^https?:\/\/docs\.google\.com\/forms\/d\/([a-zA-Z0-9_-]{20,})(?:\/|$)/i

const FORM_ID_PATTERN = /^[a-zA-Z0-9_-]{20,}$/

export function isValidGoogleFormRef(value: string): boolean {
  const trimmed = value.trim()
  if (!trimmed) {
    return false
  }

  return FORM_URL_PATTERN.test(trimmed) || FORM_ID_PATTERN.test(trimmed)
}

export function normalizeGoogleFormRef(value: string): string {
  const trimmed = value.trim()
  const match = trimmed.match(FORM_URL_PATTERN)

  if (match?.[1]) {
    return match[1]
  }

  return trimmed
}
