import { computed } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import type { OrderBy } from 'frappe-ui'

const defaultDiscussionOrderBy: OrderBy = 'last_post_at desc'

const sortChoices: { label: string; value: OrderBy }[] = [
  { label: 'Newest first', value: 'last_post_at desc' },
  { label: 'Oldest first', value: 'last_post_at asc' },
  { label: 'Creation date', value: 'creation desc' },
]

const storedOrderBy = useLocalStorage<OrderBy>('gameplan:discussionSort', defaultDiscussionOrderBy)

export const discussionSortOptions = [
  { label: 'Sort by', value: '' as const, disabled: true },
  ...sortChoices,
]

export const discussionOrderBy = computed<OrderBy>({
  get: () => normalizeDiscussionOrderBy(storedOrderBy.value),
  set: (value) => {
    storedOrderBy.value = normalizeDiscussionOrderBy(value)
  },
})

function normalizeDiscussionOrderBy(value: unknown): OrderBy {
  const match = sortChoices.find((choice) => choice.value === value)
  return match ? match.value : defaultDiscussionOrderBy
}
