import { getCurrentScope, onScopeDispose } from 'vue'
import {
  useCall as frappeUseCall,
  useDoc as frappeUseDoc,
  useList as frappeUseList,
} from 'frappe-ui'
import { isOnline, onReconnect } from './online'
import { isNetworkError } from '@/offline'
import { getSessionUserFromCookie } from '@/utils/sessionCookie'

/**
 * frappe-ui's resources, made offline-aware: no request while offline, the cached copy kept
 * when the network fails, cached per user, and what is on screen revalidated on reconnect.
 * Import `useList`, `useDoc` and `useCall` from here.
 */

/**
 * Rejects API requests while offline as a failed fetch would, so resources fall back to their
 * cached copy. frappe-ui has no hook before its fetch, so this wraps the global one, on import
 * because shared stores fetch as soon as their modules load.
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

/**
 * `use` with the offline defaults every cached resource here wants:
 * - `staleOnError`, which frappe-ui applies to network failures only, never to an error the
 *   server answers with, so a lost permission still clears the cached copy;
 * - the cache key scoped to the signed-in user, so another account on this browser can't read
 *   it offline;
 * - revalidation on reconnect, except for `immediate: false` resources: those are actions or
 *   on-demand calls, and replaying one could repeat a write.
 */
function offlineAware<F extends (options: any) => any>(use: F): F {
  return ((options) => {
    const { cacheKey } = options
    const resource = use({
      staleOnError: true,
      ...options,
      cacheKey: cacheKey && [cacheKey].flat().concat(getSessionUserFromCookie()),
    })
    return options.immediate === false ? resource : revalidateOnReconnect(resource)
  }) as F
}

export const useList = offlineAware(frappeUseList)
export const useDoc = offlineAware(frappeUseDoc)
export const useCall = offlineAware(frappeUseCall)
