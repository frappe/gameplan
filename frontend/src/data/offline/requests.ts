/**
 * Refuses API requests while offline, the way a dropped connection would, so resources fall
 * back to their cached copy at once instead of waiting for a timeout. frappe-ui has no hook
 * before its fetch, so this wraps the global one, on import, because shared stores fetch as
 * soon as their modules load.
 */
import { toast } from 'frappe-ui'
import { isOnline } from '../online'

export const OFFLINE_ACTION_MESSAGE = "You're offline. Reconnect to do this."

/** What a request refused offline rejects with. A dialog awaiting it shows the message. */
export class OfflineError extends TypeError {
  constructor() {
    super(OFFLINE_ACTION_MESSAGE)
  }
}

/** A request that never reached the server: refused offline, or a failed fetch. */
export function isNetworkError(error: unknown) {
  // Chrome, Safari and Firefox each word a failed fetch differently.
  return (
    error instanceof OfflineError ||
    (error instanceof TypeError && /Failed to fetch|Load failed|NetworkError/.test(error.message))
  )
}

const fetch = window.fetch.bind(window)

window.fetch = (input, init) => {
  if (isOnline.value || !isApiRequest(input)) return fetch(input, init)
  // Said once, and only for a write the person just asked for, not for background reads.
  if (isWrite(input, init) && (navigator.userActivation?.isActive ?? true)) {
    toast.warning(OFFLINE_ACTION_MESSAGE, { id: 'offline-action' })
  }
  return Promise.reject(new OfflineError())
}

function isApiRequest(input: RequestInfo | URL) {
  const url = new URL(input instanceof Request ? input.url : input, window.location.origin)
  return url.origin === window.location.origin && url.pathname.startsWith('/api/')
}

function isWrite(input: RequestInfo | URL, init?: RequestInit) {
  const method = init?.method ?? (input instanceof Request ? input.method : 'GET')
  return !['GET', 'HEAD'].includes(method.toUpperCase())
}
