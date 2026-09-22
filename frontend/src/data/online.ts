import { useDebounceFn, useNetwork } from '@vueuse/core'
import { getCurrentScope, onScopeDispose, watch } from 'vue'

// Single shared reading of the browser's network state for the whole app (US3's indicator
// and US5's reconnect refetch both read `isOnline`).
const network = useNetwork()

export const isOnline = network.isOnline

/** Data Saver: the person has asked their browser not to fetch what it was not asked for. */
export const saveData = network.saveData

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
 * Returns an unregister function for a pending request.
 *
 * A pending request is dropped when the calling component unmounts, but only where there is
 * a scope to tie it to: called after an `await`, as it is from DiscussionView's visit
 * tracking, there is none, and the request is sent on reconnect whether or not the caller is
 * still on screen. Unregister it yourself where that matters.
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
