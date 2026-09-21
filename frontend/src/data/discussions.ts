import { MaybeRefOrGetter, ref, toValue, watch } from 'vue'
import { revalidateOnReconnect, useDoc, useList } from '@/data/offlineRevalidation'
import { UseListOptions } from 'frappe-ui'
import { useDocumentVisibility } from '@vueuse/core'
import { GPDiscussion } from '@/types/doctypes'
import { session } from './session'

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

export interface Discussion extends GPDiscussion {
  project_title: string
  last_post_at: string
  unread: number
  last_comment_content?: string
  last_poll_title?: string
}

export type FeedType = 'recent' | 'unread' | 'participating'

const FEED_TYPES: FeedType[] = ['recent', 'unread', 'participating']

/**
 * Where each feed caches its rows. Shared with offline downloads, which fills the same
 * entries so a Space the device has never opened still lists its discussions offline.
 */
export const spaceFeedKey = (spaceId: string | number) => `SpaceDiscussions-${spaceId}`
export const communityFeedKey = (communityId: string, feedType: FeedType = 'recent') =>
  `Discussions-${communityId}-${feedType}`

/** What a feed key covers, for offline downloads deciding which rows belong in it. */
export function feedScope(
  key: string,
): { space?: string; community?: string; feedType?: FeedType } | null {
  const space = /^SpaceDiscussions-(.+)$/.exec(key)
  if (space) return { space: space[1] }
  const community = new RegExp(`^Discussions-(.+)-(${FEED_TYPES.join('|')})$`).exec(key)
  return community ? { community: community[1], feedType: community[2] as FeedType } : null
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
    // Per user for every feed, so another account on this browser can't read them offline.
    cacheKey: options.cacheKey ? ['Discussions', options.cacheKey, session.user] : undefined,
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
  } else {
    // Reused by a later mount, which revalidates it on reconnect too.
    revalidateOnReconnect(discussionsCache[name])
  }
  return discussionsCache[name] as ReturnType<typeof useDoc<Discussion, DiscussionMethods>>
}
