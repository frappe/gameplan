import { MaybeRefOrGetter, toValue } from 'vue'
import { useDoc, useList } from 'frappe-ui/src/data-fetching'
import { UseListOptions } from 'frappe-ui/src/data-fetching/useList/types'
import { GPDiscussion } from '@/types/doctypes'

export interface Discussion extends GPDiscussion {
  project_title: string
  last_visit: string
  last_post_at: string
  unread: boolean
  last_comment_content?: string
  last_poll_title?: string
}

export type UseDiscussionOptions = Pick<
  UseListOptions<Discussion>,
  'cacheKey' | 'filters' | 'limit' | 'orderBy' | 'immediate'
>

export function useDiscussions(options: UseDiscussionOptions) {
  const discussions = useList<Discussion>({
    url: '/api/v2/method/gameplan.gameplan.doctype.gp_discussion.api.get_discussions',
    doctype: 'GP Discussion',
    cacheKey: options.cacheKey ? ['Discussions', options.cacheKey] : undefined,
    filters: options.filters,
    limit: options.limit || 50,
    orderBy: options.orderBy,
    immediate: options.immediate ?? true,
    transform(data) {
      return data.map((d) => ({
        ...d,
        unread: !d.last_visit || d.last_post_at > d.last_visit,
      }))
    },
  })
  return discussions
}

let discussionsCache: Record<string, ReturnType<typeof useDoc>> = {}

export function useDiscussion(discussionId: MaybeRefOrGetter<string>) {
  interface Discussion extends GPDiscussion {
    last_unread_comment: string
    last_unread_poll: string
    is_bookmarked: boolean
  }

  interface DiscussionMethods {
    trackVisit: () => void
    closeDiscussion: () => void
    reopenDiscussion: () => void
    pinDiscussion: () => void
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
      methods: {
        trackVisit: 'track_visit',
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
