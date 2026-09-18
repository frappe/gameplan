import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { isNetworkError } from '@/offline'
import { isOnline } from './online'

interface LoadableResource {
  loading: boolean
  error: unknown
  isFinished?: boolean
  data?: unknown
  doc?: unknown
}

/** A failure caused by being offline rather than by the server. */
export function isOfflineError(error: unknown) {
  return !isOnline.value || isNetworkError(error)
}

/** The copy every "couldn't load" state uses, so pages word it the same way. */
export function loadFailureCopy(what: string, offline: boolean) {
  return offline
    ? {
        title: `Can't load ${what} while offline`,
        message: "It hasn't been saved for offline use yet. Reconnect and retry to load it.",
      }
    : {
        title: `Could not load ${what}`,
        message: 'Something went wrong while loading this. Retry to try again.',
      }
}

/**
 * A fetch that failed with nothing cached to show in its place. Without this the page
 * renders as empty (or blank), which reads as "there's nothing here" rather than
 * "this couldn't be loaded".
 */
export function useLoadFailure(
  resource: MaybeRefOrGetter<LoadableResource | null | undefined>,
  what: string,
) {
  return computed(() => {
    const r = toValue(resource)
    if (!r || r.loading || !r.error || r.isFinished === false) return null
    if (('doc' in r ? r.doc : r.data) != null) return null
    return loadFailureCopy(what, isOfflineError(r.error))
  })
}
