import { useDebounceFn, useNetwork } from '@vueuse/core'
import { getCurrentScope, onScopeDispose, watch } from 'vue'

// One reading of the network state for the whole app.
const network = useNetwork()

export const isOnline = network.isOnline

/** Data Saver is on. */
export const saveData = network.saveData

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

const notifyReconnect = useDebounceFn(() => {
  // It may have dropped again during the debounce.
  if (!isOnline.value) return
  for (const callback of callbacks) {
    try {
      callback()
    } catch (error) {
      console.error('onReconnect callback failed', error)
    }
  }
}, RECONNECT_DEBOUNCE_MS)

watch(isOnline, (online) => {
  if (online) notifyReconnect()
})
