import { ref } from 'vue'
import { useList } from '@/data/offlineRevalidation'
import type { OrderBy } from 'frappe-ui'
import type { GPUserProfile } from '@/types/doctypes'

export interface Person extends Pick<
  GPUserProfile,
  'name' | 'user' | 'bio' | 'modified' | 'cover_image' | 'cover_image_position'
> {
  discussions_count: number
  comments_count: number
  reactions_given: number
  reactions_received: number
}

/** Server sort order. Post, reply and reaction counts aren't columns, so People.vue sorts those. */
export const peopleOrderBy = ref<OrderBy>('modified desc')

/** The People list: server-sorted, filtered to enabled accounts, cached for offline use. */
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
  cacheKey: 'People',
  immediate: true,
})
