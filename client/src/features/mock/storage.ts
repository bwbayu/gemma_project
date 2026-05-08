const KEY_PREFIX = 'physicsanimator.client'

export function getStorageKey(resource: string): string {
  return `${KEY_PREFIX}.${resource}`
}

export function readStorage<T>(resource: string, fallback: T): T {
  const raw = window.localStorage.getItem(getStorageKey(resource))
  if (!raw) {
    return fallback
  }

  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

export function writeStorage<T>(resource: string, value: T): void {
  window.localStorage.setItem(getStorageKey(resource), JSON.stringify(value))
}
