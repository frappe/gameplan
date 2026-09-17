import { getCurrentScope, onScopeDispose } from 'vue'
import {
  useCall as frappeUseCall,
  useDoc as frappeUseDoc,
  useList as frappeUseList,
} from 'frappe-ui'
import { isOnline, onReconnect } from './online'
import { isNetworkError } from '@/offline'

/**
 * Stale-while-revalidate for offline use: resources show their cached copy right away, API
 * requests are not sent while offline, and whatever is on screen revalidates on reconnect.
 *
 * Import `useList`, `useDoc` and `useCall` from here instead of from frappe-ui.
 */

/**
 * Rejects API requests while offline the way a failed fetch would, without sending them.
 * Resources still fall back to their cached copy (`staleOnError`) or the offline empty state.
 * frappe-ui has no hook before its fetch, so this wraps the global one. Installed on import,
 * because shared stores start fetching as soon as their modules load.
 */
function holdRequestsWhileOffline() {
  const fetch = window.fetch.bind(window)
  window.fetch = (input, init) => {
    if (!isOnline.value && isApiRequest(input)) {
      return Promise.reject(new TypeError('Failed to fetch'))
    }
    return fetch(input, init)
  }
}

holdRequestsWhileOffline()

function isApiRequest(input: RequestInfo | URL) {
  const url = new URL(input instanceof Request ? input.url : input, window.location.origin)
  return url.origin === window.location.origin && url.pathname.startsWith('/api/')
}

interface Revalidatable {
  reload: () => unknown
  loading: boolean
  isFinished: boolean
  error: unknown
}

/**
 * Reloads `resource` once the connection returns. A resource used by a component revalidates
 * while that component is mounted. One created outside a component (a shared store) only
 * revalidates if its own request failed offline.
 */
export function revalidateOnReconnect<T extends Revalidatable>(resource: T): T {
  const mounted = Boolean(getCurrentScope())
  const unregister = onReconnect(() => {
    // Never loaded (e.g. waiting on a name), or already refreshing.
    if (!resource.isFinished || resource.loading) return
    if (mounted || isNetworkError(resource.error)) resource.reload()
  })
  if (mounted) onScopeDispose(unregister)
  return resource
}

// Resources with `immediate: false` are actions or on-demand calls: replaying one on reconnect
// could repeat a write, so only resources that load themselves revalidate.
export const useList = ((options) => {
  const list = frappeUseList(options)
  return options.immediate === false ? list : revalidateOnReconnect(list)
}) as typeof frappeUseList

export const useDoc = ((options) => {
  const doc = frappeUseDoc(options)
  return options.immediate === false ? doc : revalidateOnReconnect(doc)
}) as typeof frappeUseDoc

export const useCall = ((options) => {
  const call = frappeUseCall(options)
  return options.immediate === false ? call : revalidateOnReconnect(call)
}) as typeof frappeUseCall
