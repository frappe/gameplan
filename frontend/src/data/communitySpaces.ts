import { computed, reactive } from 'vue'
import { useCall } from 'frappe-ui'
import { communityState } from './communityState'
import { joinedSpaces, spaces } from './spaces'
import {
  currentHideInactiveSpaces,
  currentSpaceSidebarSort,
  type SpaceSidebarSort,
} from './sidebarPreferences'
import type { Space } from './spaces'

const INACTIVE_SPACE_MONTHS = 2

const spaceActivity = useCall<Record<string, string | null>>({
  url: '/api/v2/method/GP Project/get_activity',
  cacheKey: 'spaceActivity',
  staleOnError: true,
  initialData: {},
  immediate: true,
})

const availableCommunitySpaceList = computed(() => {
  if (!communityState.id) {
    return []
  }

  return (spaces.data || []).filter((space) => {
    return !space.archived_at && space.team === communityState.id
  })
})

const communitySpaceList = computed(() => {
  let visibleSpaces = availableCommunitySpaceList.value

  if (currentHideInactiveSpaces.value && !spaceActivity.loading) {
    visibleSpaces = visibleSpaces.filter(hasRecentActivity)
  }

  return sortSpaces(visibleSpaces, currentSpaceSidebarSort.value)
})

const archivedCommunitySpaceList = computed(() => {
  if (!communityState.id) {
    return []
  }

  return (spaces.data || []).filter((space) => {
    return space.archived_at && space.team === communityState.id
  })
})

const joinedCommunitySpaceList = computed(() => {
  return availableCommunitySpaceList.value.filter((space) =>
    joinedSpaces.data?.includes(space.name),
  )
})

const communitySpaceOptions = computed(() => {
  return availableCommunitySpaceList.value.map((space) => ({
    label: space.title,
    value: space.name,
    icon: space.icon,
  }))
})

const hasHiddenInactiveSpaces = computed(() => {
  return (
    currentHideInactiveSpaces.value &&
    !spaceActivity.loading &&
    availableCommunitySpaceList.value.some(isInactiveSpace)
  )
})

const communitySpacesEmptyMessage = computed(() => {
  if (hasHiddenInactiveSpaces.value) {
    return `No spaces active in the last ${INACTIVE_SPACE_MONTHS} months.`
  }

  if (archivedCommunitySpaceList.value.length > 0) {
    return 'All spaces in this community are archived.'
  }

  return 'No spaces in this community yet.'
})

export const communitySpaces = reactive({
  list: communitySpaceList,
  archived: archivedCommunitySpaceList,
  joined: joinedCommunitySpaceList,
  options: communitySpaceOptions,
  hasHiddenInactive: hasHiddenInactiveSpaces,
  emptyMessage: communitySpacesEmptyMessage,
})

function sortSpaces(spaceList: Space[], sort: SpaceSidebarSort) {
  return [...spaceList].sort((left, right) => {
    if (sort === 'Recent activity') {
      let leftActivity = getActivityTime(left.name)
      let rightActivity = getActivityTime(right.name)
      if (leftActivity !== rightActivity) {
        return rightActivity - leftActivity
      }
    }

    return left.title.localeCompare(right.title)
  })
}

function hasRecentActivity(space: Space) {
  return !isInactiveSpace(space)
}

function isInactiveSpace(space: Space) {
  let activity = getActivityTime(space.name)
  return !activity || activity < getInactiveCutoffTime()
}

function getActivityTime(spaceId: string) {
  let lastActivityAt = spaceActivity.data?.[spaceId]
  if (!lastActivityAt) return 0

  let time = new Date(lastActivityAt).getTime()
  return Number.isFinite(time) ? time : 0
}

function getInactiveCutoffTime() {
  let cutoff = new Date()
  cutoff.setMonth(cutoff.getMonth() - INACTIVE_SPACE_MONTHS)
  return cutoff.getTime()
}
