import { ref, watch } from 'vue'
import { useDoc, useList } from 'frappe-ui'
import { UseListOptions } from 'frappe-ui'
import { useDocumentVisibility } from '@vueuse/core'
import { GPDiscussion } from '@/types/doctypes'
import { createSharedDoc } from './sharedDoc'

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

interface DiscussionDoc extends GPDiscussion {
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

/** The discussion behind `discussionId`, followed as that id changes. */
export const useDiscussion = createSharedDoc((name: string) =>
  useDoc<DiscussionDoc, DiscussionMethods>({
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
  }),
)
