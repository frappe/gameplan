import { computed } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import type { DropdownOptions, OrderBy } from 'frappe-ui'

const defaultDiscussionOrderBy: OrderBy = 'last_post_at desc'

const sortChoices: { label: string; value: OrderBy }[] = [
  { label: 'Latest activity', value: 'last_post_at desc' },
  { label: 'Oldest activity', value: 'last_post_at asc' },
  { label: 'Newest created', value: 'creation desc' },
]

const storedOrderBy = useLocalStorage<OrderBy>('gameplan:discussionSort', defaultDiscussionOrderBy)

export const discussionOrderBy = computed<OrderBy>({
  get: () => normalizeDiscussionOrderBy(storedOrderBy.value),
  set: (value) => {
    storedOrderBy.value = normalizeDiscussionOrderBy(value)
  },
})

export const discussionSortLabel = computed(
  () => sortChoices.find((choice) => choice.value === discussionOrderBy.value)!.label,
)

export const discussionSortMenuOptions = computed<DropdownOptions>(() => [
  {
    group: 'Sort by',
    options: sortChoices.map((choice) => ({
      label: choice.label,
      icon: discussionOrderBy.value === choice.value ? 'lucide-check' : null,
      onClick: () => (discussionOrderBy.value = choice.value),
    })),
  },
])

function normalizeDiscussionOrderBy(value: unknown): OrderBy {
  const match = sortChoices.find((choice) => choice.value === value)
  return match ? match.value : defaultDiscussionOrderBy
}
