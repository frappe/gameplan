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

/** Says the action can't be done offline. Returns whether it was refused. */
export function refuseOffline() {
  if (isOnline.value) return false
  toast.warning(OFFLINE_ACTION_MESSAGE, { id: 'offline-action' })
  return true
}

/** A request that never reached the server: refused offline, or a failed fetch. */
export function isNetworkError(error: unknown) {
  // Chrome, Safari and Firefox each word a failed fetch differently.
  return (
    error instanceof OfflineError ||
    (error instanceof TypeError && /Failed to fetch|Load failed|NetworkError/.test(error.message))
  )
}

// The HTTP method can't tell a person's action from a page loading: `call()` reads over POST,
// and opening a page sends writes of its own (track_visit). So a write counts as asked for
// only if it starts soon after a click or key press, on the page where it happened. Long
// enough for the one-second batching of reactions.
const ACTION_WINDOW_MS = 1500
let gesture = { at: -Infinity, url: '' }

function recordGesture(event: Event) {
  if (event instanceof KeyboardEvent && !['Enter', ' '].includes(event.key)) return
  gesture = { at: performance.now(), url: location.href }
}
window.addEventListener('click', recordGesture, { capture: true })
window.addEventListener('keydown', recordGesture, { capture: true })

function isAskedFor(input: RequestInfo | URL, init?: RequestInit) {
  return (
    isWrite(input, init) &&
    performance.now() - gesture.at < ACTION_WINDOW_MS &&
    location.href === gesture.url
  )
}

const fetch = window.fetch.bind(window)

window.fetch = (input, init) => {
  if (isOnline.value || !isApiRequest(input)) return fetch(input, init)
  if (isAskedFor(input, init)) refuseOffline()
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
