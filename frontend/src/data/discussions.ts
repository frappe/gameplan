import { ref, watch } from 'vue'
import { revalidateOnReconnect } from '@/data/offline/resources'
import { type CacheKey, UseListOptions, useDoc, useList } from 'frappe-ui'
import { useDocumentVisibility } from '@vueuse/core'
import { GPDiscussion } from '@/types/doctypes'

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

export const FEED_LIMIT = 50
export const discussionFeedKey = (name: CacheKey) => ['Discussions', name]
export const pinnedFeedKey = (name: CacheKey) => ['pinned', name]
// Community pins also appear in their own Space.
export const pinScopes = (space: boolean) => (space ? ['Space', 'Category'] : ['Category'])

export interface DiscussionFeedRow {
  project?: string | number
  team?: string
  last_post_at?: string
  pinned_at?: string | null
  pin_scope?: string
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

export interface DiscussionFeed {
  key: string
  space?: string
  community?: string
  pinned: boolean
  filtered?: boolean
}

/** Scope and pin rules of a cached feed, shared by online feeds and downloads. */
export function feedScope(key: unknown): Omit<DiscussionFeed, 'key'> | null {
  const inner = Array.isArray(key) ? key[1] : key
  const pinned = Array.isArray(inner) && inner[0] === 'pinned'
  const name = pinned ? inner[1] : inner
  if (typeof name !== 'string') return null
  const space = /^SpaceDiscussions-(.+)$/.exec(name)
  if (space) return { space: space[1], pinned }
  const community = new RegExp(`^Discussions-(.+)-(${FEED_TYPES.join('|')})$`).exec(name)
  return community ? { community: community[1], pinned, filtered: community[2] !== 'recent' } : null
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
    cacheKey: options.cacheKey ? discussionFeedKey(options.cacheKey) : undefined,
    filters: options.filters,
    limit: options.limit || FEED_LIMIT,
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

// Cached per discussion, so the id is a plain string: a cached doc bound to a getter follows
// whatever the getter returns later and ends up showing another discussion under this id.
export function useDiscussion(name: string) {
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

  if (!discussionsCache[name]) {
    discussionsCache[name] = useDoc<Discussion, DiscussionMethods>({
      doctype: 'GP Discussion',
      name,
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
