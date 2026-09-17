import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { isBrowserOffline, isNetworkError } from '@/offline'

interface LoadableResource {
  loading: boolean
  error: unknown
  isFinished?: boolean
  data?: unknown
  doc?: unknown
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

    return isBrowserOffline() || isNetworkError(r.error)
      ? {
          title: `Can't load ${what} while offline`,
          message: "It hasn't been saved for offline use yet. Reconnect and retry to load it.",
        }
      : {
          title: `Could not load ${what}`,
          message: 'Something went wrong while loading this. Retry to try again.',
        }
  })
}
