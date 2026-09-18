import { useDebounceFn, useOnline } from '@vueuse/core'
import { getCurrentScope, onScopeDispose, watch } from 'vue'

// Single shared `navigator.onLine` + online/offline event listener for the whole
// app (US3's indicator and US5's reconnect refetch both read this).
export const isOnline = useOnline()

// Flaky connectivity (a train tunnel, a flapping wifi radio) can fire several
// offline→online transitions within a second or two. Debouncing the notification
// (not the ref itself, so the indicator stays instantly responsive) means a
// stampede of refetches only fires once connectivity actually settles.
const RECONNECT_DEBOUNCE_MS = 1500

type ReconnectCallback = () => void
const callbacks = new Set<ReconnectCallback>()

/** Runs `callback` when the connection returns (debounced). Returns an unregister function. */
export function onReconnect(callback: ReconnectCallback): () => void {
  callbacks.add(callback)
  return () => callbacks.delete(callback)
}

/**
 * Sends `request` now, or once when the connection returns instead of attempting it offline.
 * A pending request is dropped if the calling component unmounts first.
 */
export function whenOnline(request: () => void) {
  if (isOnline.value) return request()
  const unregister = onReconnect(() => {
    unregister()
    request()
  })
  if (getCurrentScope()) onScopeDispose(unregister)
}

const notifyReconnect = useDebounceFn(() => {
  // Re-check at fire time: connectivity may have dropped again during the
  // debounce window, in which case there's nothing to reconnect yet.
  if (!isOnline.value) return
  for (const callback of callbacks) {
    try {
      callback()
    } catch (error) {
      console.error('onReconnect callback failed', error)
    }
  }
}, RECONNECT_DEBOUNCE_MS)

// watch() (not `immediate`) only fires on actual changes, so this is inert on
// initial load and only triggers on a genuine offline→online flip.
watch(isOnline, (online) => {
  if (online) notifyReconnect()
})
