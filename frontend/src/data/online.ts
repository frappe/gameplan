import { toast } from 'frappe-ui'
import { useNetwork, watchDebounced } from '@vueuse/core'
import { getCurrentScope, onScopeDispose } from 'vue'

// One reading of the network state for the whole app.
const network = useNetwork()

export const isOnline = network.isOnline

// A flapping connection flips several times a second. The callbacks are debounced, not
// the ref, so the banner stays instant while refetches wait for the network to settle.
const RECONNECT_DEBOUNCE_MS = 1500

type ReconnectCallback = () => void
const callbacks = new Set<ReconnectCallback>()

/** Runs `callback` when the connection returns (debounced). Returns an unregister function. */
export function onReconnect(callback: ReconnectCallback): () => void {
  callbacks.add(callback)
  return () => callbacks.delete(callback)
}

/**
 * Sends `request` now, or once the connection returns. A pending request is dropped when the
 * calling scope ends; called after an `await` there is none, so unregister it yourself.
 */
export function whenOnline(request: () => void) {
  if (isOnline.value) {
    request()
    return () => {}
  }
  const unregister = onReconnect(() => {
    unregister()
    request()
  })
  if (getCurrentScope()) onScopeDispose(unregister)
  return unregister
}

// Only once the connection has settled: a flap back offline inside the wait cancels it.
watchDebounced(
  isOnline,
  (online) => {
    if (!online) return
    for (const callback of callbacks) {
      try {
        callback()
      } catch (error) {
        console.error('onReconnect callback failed', error)
      }
    }
  },
  { debounce: RECONNECT_DEBOUNCE_MS },
)

const OFFLINE_ACTION_MESSAGE = "You're offline. Reconnect to do this."

/** Says the action can't be done offline. Returns whether it was refused. */
export function refuseOffline() {
  if (isOnline.value) return false
  toast.warning(OFFLINE_ACTION_MESSAGE, { id: 'offline-action' })
  return true
}

/** A failed fetch that never reached the server. */
export function isNetworkError(error: unknown) {
  // Chrome, Safari and Firefox each word a failed fetch differently.
  return (
    error instanceof TypeError && /Failed to fetch|Load failed|NetworkError/.test(error.message)
  )
}
