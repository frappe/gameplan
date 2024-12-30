import { ref, Ref, watch } from 'vue'
import { createListResource } from 'frappe-ui'
import { GPDiscussion } from '@/types/doctypes'

interface Discussion extends GPDiscussion {
  last_visit: string
}

interface UseDiscussionOptions {
  cacheKey?: any
  filters?: Record<string, any>
  pageLength?: number
  orderBy?: string
}

interface ListResource {
  data: Discussion[]
  loading: boolean
  reload: () => void
}

export function useDiscussions({
  filters = {},
  pageLength = 50,
  orderBy = 'last_post_at desc',
}: UseDiscussionOptions = {}): Ref<ListResource> {
  let cacheKey = JSON.stringify({ filters, pageLength, orderBy })
  let discussions = ref<ListResource>(
    _createListResource({ filters, pageLength, orderBy, cacheKey }),
  )

  watch(
    () => {
      return { filters, pageLength, orderBy }
    },
    () => {
      let cacheKey = JSON.stringify({ filters, pageLength, orderBy })
      discussions.value = _createListResource({ filters, pageLength, orderBy, cacheKey })
    },
  )
  return discussions
}

function _createListResource({ filters, pageLength, orderBy, cacheKey }: UseDiscussionOptions) {
  return createListResource({
    type: 'list',
    doctype: 'GP Discussion',
    cache: ['Discussions', cacheKey],
    url: 'gameplan.gameplan.doctype.gp_discussion.api.get_discussions',
    filters: filters,
    auto: true,
    pageLength: pageLength || 50,
    orderBy: orderBy,
    transform(data: Discussion[]) {
      return data.map((d) => ({
        ...d,
        unread: !d.last_visit || d.last_post_at > d.last_visit,
      }))
    },
  })
}
