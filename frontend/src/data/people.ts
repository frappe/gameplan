import { computed, ref } from 'vue'
import { useList } from 'frappe-ui'
import type { OrderBy } from 'frappe-ui'
import type { GPUserProfile } from '@/types/doctypes'

interface Person extends Pick<
  GPUserProfile,
  'name' | 'user' | 'bio' | 'modified' | 'cover_image' | 'cover_image_position'
> {
  discussions_count: number
  comments_count: number
  reactions_given: number
  reactions_received: number
}

type PeopleSortOption =
  | { label: string; value: OrderBy; count?: never }
  // Counts aren't columns, so the server can't order by them. People.vue sorts these.
  | {
      label: string
      value: string
      count: 'discussions_count' | 'comments_count' | 'reactions_received'
    }

export const peopleSortOptions: PeopleSortOption[] = [
  { label: 'Name', value: 'full_name asc' },
  { label: 'Last updated', value: 'modified desc' },
  { label: 'Posts', value: 'posts', count: 'discussions_count' },
  { label: 'Replies', value: 'replies', count: 'comments_count' },
  { label: 'Reactions received', value: 'reactions_received', count: 'reactions_received' },
]

const defaultSort = peopleSortOptions[1]

/** The selected People sort: a `peopleSortOptions` value. */
export const peopleSort = ref(defaultSort.value)

export const peopleSortOption = computed(
  () => peopleSortOptions.find((option) => option.value === peopleSort.value) ?? defaultSort,
)

/** The People list: server-sorted, filtered to enabled accounts, shared across visits.
 *  People.vue reloads it on each visit. */
export const people = useList<Person>({
  // GP User Profile's default list view; the aggregate post/reply/reaction counts are
  // computed server-side per row, so this can't be the generic `/api/v2/document/...`
  // REST list.
  url: '/api/v2/method/gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_list',
  doctype: 'GP User Profile',
  fields: ['name', 'user', 'bio', 'modified', 'cover_image', 'cover_image_position'],
  filters: { enabled: 1 },
  orderBy: () => serverOrder(peopleSortOption.value),
  limit: 999,
  cacheKey: 'People',
  immediate: false,
})

function serverOrder(option: PeopleSortOption): OrderBy {
  return option.count ? 'modified desc' : option.value
}
