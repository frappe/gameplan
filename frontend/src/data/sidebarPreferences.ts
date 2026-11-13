import { computed, ref } from 'vue'
import type { DropdownOptions } from 'frappe-ui'
import { normalizeBoolean, ProfilePreference } from './profilePreference'

export type SidebarBadgeStyle = 'Unread count' | 'Dot'
export type SpaceSidebarSort = 'Recent activity' | 'Alphabetical'

const defaultSidebarBadgeStyle: SidebarBadgeStyle = 'Dot'
const sidebarBadgeStyle = ref<SidebarBadgeStyle>(defaultSidebarBadgeStyle)
const defaultSpaceSidebarSort: SpaceSidebarSort = 'Recent activity'
const spaceSidebarSort = new ProfilePreference<SpaceSidebarSort>({
  field: 'space_sidebar_sort',
  defaultValue: defaultSpaceSidebarSort,
  normalize: normalizeSpaceSidebarSort,
  legacyKey: 'gameplan:spaceSidebarSort',
})
const hideInactiveSpaces = new ProfilePreference<boolean>({
  field: 'hide_inactive_spaces',
  defaultValue: false,
  normalize: normalizeBoolean,
  legacyKey: 'gameplan:hideInactiveSpaces',
})
const showAllDiscussions = new ProfilePreference<boolean>({
  field: 'show_all_discussions',
  defaultValue: false,
  normalize: normalizeBoolean,
  legacyKey: 'gameplan:showAllDiscussions',
})

export const currentSidebarBadgeStyle = computed(() => sidebarBadgeStyle.value)
export const currentSpaceSidebarSort = spaceSidebarSort.current
export const currentHideInactiveSpaces = hideInactiveSpaces.current
/** Whether the rail and mobile home offer the feed that spans every joined community. */
export const currentShowAllDiscussions = showAllDiscussions.current

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

interface SidebarPreferenceFields {
  user_profile: string
  sidebar_badge_style?: unknown
  space_sidebar_sort?: unknown
  hide_inactive_spaces?: unknown
  show_all_discussions?: unknown
}

/** Applies the sidebar preferences saved on the session user's profile. */
export function loadSidebarPreferences(user: SidebarPreferenceFields) {
  setSidebarBadgeStyle(user.sidebar_badge_style)
  spaceSidebarSort.load(user.space_sidebar_sort, user.user_profile)
  hideInactiveSpaces.load(user.hide_inactive_spaces, user.user_profile)
  showAllDiscussions.load(user.show_all_discussions, user.user_profile)
}

export function setSidebarBadgeStyle(style: unknown) {
  sidebarBadgeStyle.value = normalizeSidebarBadgeStyle(style)
}

export function setSpaceSidebarSort(sort: unknown) {
  spaceSidebarSort.set(normalizeSpaceSidebarSort(sort))
}

export function setHideInactiveSpaces(value: boolean) {
  hideInactiveSpaces.set(value)
}

export function setShowAllDiscussions(value: boolean) {
  showAllDiscussions.set(value)
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
