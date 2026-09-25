/**
 * frappe-ui's resources with the offline defaults. Import `useList`, `useDoc` and `useCall`
 * from here rather than from frappe-ui.
 */
import { getCurrentScope, onScopeDispose } from 'vue'
import { get } from 'idb-keyval'
import {
  useCall as frappeUseCall,
  useDoc as frappeUseDoc,
  useList as frappeUseList,
} from 'frappe-ui'
import { onReconnect } from '../online'
import { isNetworkError } from './requests'
import { callKey, listKey } from './cache'

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
 * `use` with the offline defaults:
 * - `staleOnError`, which frappe-ui applies to network failures only, never to an error the
 *   server answers with, so a lost permission still clears the cached copy;
 * - `cacheLoaded`, resolving to the cached copy (or null) once the cache has been read;
 * - revalidation on reconnect, except for `immediate: false` resources: those are actions or
 *   on-demand calls, and replaying one could repeat a write.
 */
function offlineAware<F extends (options: any) => any>(
  use: F,
  keyOf?: (cacheKey: unknown[]) => string,
): F {
  return ((options) => {
    const resource = use({ staleOnError: true, ...options })
    if (keyOf && options.cacheKey) {
      resource.cacheLoaded = get(keyOf([options.cacheKey].flat()))
        .then((stored) => (typeof stored === 'string' ? JSON.parse(stored) : null))
        .catch(() => null)
    }
    return options.immediate === false ? resource : revalidateOnReconnect(resource)
  }) as F
}

export const useList = offlineAware(frappeUseList, listKey)
export const useDoc = offlineAware(frappeUseDoc)
export const useCall = offlineAware(frappeUseCall, callKey)
