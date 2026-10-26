import { ref } from 'vue'
import { useList } from 'frappe-ui'
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

export type PeopleSortField =
  | 'full_name'
  | 'modified'
  | 'discussions_count'
  | 'comments_count'
  | 'reactions_received'
  | 'reactions_given'

type PeopleSortDirection = 'asc' | 'desc'

const sortChoices: { label: string; value: PeopleSortField }[] = [
  { label: 'Name', value: 'full_name' },
  { label: 'Last updated', value: 'modified' },
  { label: 'Posts', value: 'discussions_count' },
  { label: 'Replies', value: 'comments_count' },
  { label: 'Reactions received', value: 'reactions_received' },
  { label: 'Reactions given', value: 'reactions_given' },
]

export const peopleSortOptions = [
  { label: 'Sort by', value: '' as const, disabled: true },
  ...sortChoices,
]

export const peopleSortField = ref<PeopleSortField>('modified')
export const peopleSortDirection = ref<PeopleSortDirection>('desc')

export function sortPeopleBy(field: PeopleSortField) {
  if (peopleSortField.value === field) {
    peopleSortDirection.value = peopleSortDirection.value === 'asc' ? 'desc' : 'asc'
    return
  }
  peopleSortField.value = field
  peopleSortDirection.value = field === 'full_name' ? 'asc' : 'desc'
}

/** The People list: filtered to enabled accounts, shared across visits. People.vue sorts it
 *  and reloads it on each visit. */
export const people = useList<Person>({
  // GP User Profile's default list view; the aggregate post/reply/reaction counts are
  // computed server-side per row, so this can't be the generic `/api/v2/document/...`
  // REST list.
  url: '/api/v2/method/gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_list',
  doctype: 'GP User Profile',
  fields: ['name', 'user', 'bio', 'modified', 'cover_image', 'cover_image_position'],
  filters: { enabled: 1 },
  orderBy: 'modified desc',
  limit: 999,
  cacheKey: 'People',
  immediate: false,
})
