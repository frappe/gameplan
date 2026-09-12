import { ref } from 'vue'
import { useList } from 'frappe-ui'
import type { OrderBy } from 'frappe-ui'
import type { GPUserProfile } from '@/types/doctypes'
import { session } from './session'

export interface Person extends Pick<
  GPUserProfile,
  'name' | 'user' | 'bio' | 'modified' | 'cover_image' | 'cover_image_position'
> {
  discussions_count: number
  comments_count: number
  reactions_given: number
  reactions_received: number
}

/**
 * `full_name` and `modified` are real columns on `GP User Profile`, so the backend can
 * sort by them directly. The other Select options in People.vue (posts/replies/reactions)
 * have no backing column — they're derived counts computed per-row in `get_list` — so
 * People.vue re-sorts for those client-side after fetching at `peopleOrderBy`'s value.
 */
export const peopleOrderBy = ref<OrderBy>('modified desc')

/**
 * The People list: server-sorted, filtered to enabled accounts, cached for offline use.
 * A module-level singleton (like `data/spaces.ts`'s `spaces`) rather than a per-call
 * composable, so the People page and a future background prefetcher share one fetch and
 * one cache entry instead of racing two independent requests. To warm this cache ahead of
 * a visit, a prefetcher can `import { people } from '@/data/people'` and call
 * `people.reload()`.
 */
export const people = useList<Person>({
  // GP User Profile's default list view; the aggregate post/reply/reaction counts are
  // computed server-side per row, so this can't be the generic `/api/v2/document/...`
  // REST list.
  url: '/api/v2/method/gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_list',
  doctype: 'GP User Profile',
  fields: ['name', 'user', 'bio', 'modified', 'cover_image', 'cover_image_position'],
  filters: { enabled: 1 },
  orderBy: peopleOrderBy,
  limit: 999,
  // Scoped to the session user so a second account on the same browser can't read the
  // first account's cached People list while offline (review finding from PR #516).
  cacheKey: ['People', session.user],
  staleOnError: true,
  immediate: true,
})
