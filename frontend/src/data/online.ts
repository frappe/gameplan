import { useDebounceFn, useOnline } from '@vueuse/core'
import { watch } from 'vue'

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

/**
 * Register a callback to run when the browser transitions from offline to
 * online (debounced — see RECONNECT_DEBOUNCE_MS). Returns an unregister
 * function; call it from `onUnmounted` for callbacks owned by a component so a
 * torn-down view doesn't keep refetching after it's gone.
 */
export function onReconnect(callback: ReconnectCallback): () => void {
  callbacks.add(callback)
  return () => callbacks.delete(callback)
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
