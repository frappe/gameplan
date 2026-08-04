import { computed, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import type { DropdownOptions } from 'frappe-ui'

export type SidebarBadgeStyle = 'Unread count' | 'Dot'
export type SpaceSidebarSort = 'Recent activity' | 'Alphabetical'

const defaultSidebarBadgeStyle: SidebarBadgeStyle = 'Dot'
const sidebarBadgeStyle = ref<SidebarBadgeStyle>(defaultSidebarBadgeStyle)
const defaultSpaceSidebarSort: SpaceSidebarSort = 'Recent activity'
const spaceSidebarSort = useLocalStorage<SpaceSidebarSort>(
  'gameplan:spaceSidebarSort',
  defaultSpaceSidebarSort,
)
const hideInactiveSpaces = useLocalStorage('gameplan:hideInactiveSpaces', false)

export const currentSidebarBadgeStyle = computed(() => sidebarBadgeStyle.value)
export const currentSpaceSidebarSort = computed(() => {
  return normalizeSpaceSidebarSort(spaceSidebarSort.value)
})
export const currentHideInactiveSpaces = computed(() => hideInactiveSpaces.value)

const spaceSortValues: SpaceSidebarSort[] = ['Recent activity', 'Alphabetical']

/**
 * Menu shape for the space sort + visibility preferences.
 *
 * Shared so the sidebar's sort button and the community dropdown's submenu stay one
 * list: adding a sort order in a single place changes both.
 */
export const spaceSortMenuOptions = computed<DropdownOptions>(() => [
  {
    group: 'Sort by',
    options: spaceSortValues.map((sort) => ({
      label: sort,
      icon: currentSpaceSidebarSort.value === sort ? 'lucide-check' : null,
      onClick: () => setSpaceSidebarSort(sort),
    })),
  },
  {
    group: 'Visibility',
    options: [
      {
        label: 'Hide inactive spaces',
        description: 'No activity for 2 months',
        switch: true,
        switchValue: currentHideInactiveSpaces.value,
        onClick: setHideInactiveSpaces,
      },
    ],
  },
])

/** True when the sidebar's space list is not in its default order/visibility. */
export const hasCustomSpaceSidebarOptions = computed(() => {
  return (
    currentSpaceSidebarSort.value !== defaultSpaceSidebarSort || currentHideInactiveSpaces.value
  )
})

export function setSidebarBadgeStyle(style: unknown) {
  sidebarBadgeStyle.value = normalizeSidebarBadgeStyle(style)
}

export function setSpaceSidebarSort(sort: unknown) {
  spaceSidebarSort.value = normalizeSpaceSidebarSort(sort)
}

export function setHideInactiveSpaces(value: boolean) {
  hideInactiveSpaces.value = value
}

function normalizeSidebarBadgeStyle(style: unknown): SidebarBadgeStyle {
  if (style === 'Dot') return 'Dot'
  if (style === 'Unread count') return 'Unread count'
  return defaultSidebarBadgeStyle
}

function normalizeSpaceSidebarSort(sort: unknown): SpaceSidebarSort {
  if (sort === 'Recent activity') return 'Recent activity'
  if (sort === 'Alphabetical') return 'Alphabetical'
  return defaultSpaceSidebarSort
}
