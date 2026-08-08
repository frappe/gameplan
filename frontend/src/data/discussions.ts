import { MaybeRefOrGetter, ref, toValue, watch } from 'vue'
import { useDoc, useList } from 'frappe-ui'
import { UseListOptions } from 'frappe-ui'
import { useDocumentVisibility } from '@vueuse/core'
import { GPDiscussion } from '@/types/doctypes'
import { onReconnect } from '@/data/online'

// Reload the feed when the tab is re-activated after sitting in the background
// for at least this long, so new posts show up without a manual refresh.
const STALE_RELOAD_THRESHOLD = 2 * 60 * 1000

const reloadSignal = ref(0)

/**
 * Reload every mounted discussion feed.
 *
 * A row's read state comes from the list response, not from the unread-count store, so an
 * action taken outside a feed (marking a whole community read from the sidebar) leaves the
 * rows looking unread until they refetch. Callers used to reach into `DiscussionList` through
 * a template ref, which only works while the action lives on the same page as the list.
 */
export function reloadDiscussionLists() {
  reloadSignal.value++
}

// US5 (seamless recovery): a discussion created or updated by someone else
// while we were offline is invisible until something refetches. Mounted feeds
// pick this signal up via the reloadSignal watcher below.
onReconnect(reloadDiscussionLists)

export interface Discussion extends GPDiscussion {
  project_title: string
  last_post_at: string
  unread: number
  last_comment_content?: string
  last_poll_title?: string
}

export type UseDiscussionOptions = Pick<
  UseListOptions<Discussion>,
  'cacheKey' | 'filters' | 'limit' | 'orderBy' | 'immediate'
>

export function useDiscussions(options: UseDiscussionOptions) {
  // Track when the list was last fetched so we only reload a stale feed.
  let lastLoadedAt = Date.now()

  const discussions = useList<Discussion>({
    url: '/api/v2/method/gameplan.gameplan.doctype.gp_discussion.api.get_discussions',
    doctype: 'GP Discussion',
    cacheKey: options.cacheKey ? ['Discussions', options.cacheKey] : undefined,
    staleOnError: true,
    filters: options.filters,
    limit: options.limit || 50,
    orderBy: options.orderBy,
    immediate: options.immediate ?? true,
    onSuccess() {
      lastLoadedAt = Date.now()
    },
  })

  const visibility = useDocumentVisibility()
  watch(visibility, (state) => {
    if (state !== 'visible') return
    // Skip if it never loaded, is mid-fetch, or was refreshed recently.
    if (discussions.loading || !discussions.data) return
    if (Date.now() - lastLoadedAt < STALE_RELOAD_THRESHOLD) return
    discussions.reload()
  })

  // Only feeds that have already loaded need a refresh; an untouched one fetches on demand.
  watch(reloadSignal, () => {
    if (!discussions.data) return
    discussions.reload()
  })

  return discussions
}

let discussionsCache: Record<string, ReturnType<typeof useDoc>> = {}

export function useDiscussion(discussionId: MaybeRefOrGetter<string>) {
  interface Discussion extends GPDiscussion {
    last_unread_comment: string
    last_unread_poll: string
    is_bookmarked: boolean
    views: number
  }

  interface DiscussionMethods {
    trackVisit: () => void
    markAsUnread: () => void
    closeDiscussion: () => void
    reopenDiscussion: () => void
    pinDiscussion: (data: { pin_scope: 'Category' | 'Space' }) => void
    unpinDiscussion: () => void
    addBookmark: () => void
    removeBookmark: () => void
    moveToProject: (data: { project: string }) => void
  }

  let name = toValue(discussionId)
  if (!discussionsCache[name]) {
    discussionsCache[name] = useDoc<Discussion, DiscussionMethods>({
      doctype: 'GP Discussion',
      name: discussionId,
      staleOnError: true,
      methods: {
        trackVisit: 'track_visit',
        markAsUnread: 'mark_as_unread',
        closeDiscussion: 'close_discussion',
        reopenDiscussion: 'reopen_discussion',
        pinDiscussion: 'pin_discussion',
        unpinDiscussion: 'unpin_discussion',
        addBookmark: 'add_bookmark',
        removeBookmark: 'remove_bookmark',
        moveToProject: 'move_to_project',
      },
    })
  }
  return discussionsCache[name] as ReturnType<typeof useDoc<Discussion, DiscussionMethods>>
}
