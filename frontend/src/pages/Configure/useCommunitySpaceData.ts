import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useList } from 'frappe-ui'
import { spaces } from '@/data/spaces'
import type { GPGuestAccess, GPPage } from '@/types/doctypes'

type PageRecord = Pick<GPPage, 'project'>
type GuestAccessRecord = Pick<GPGuestAccess, 'project'>

/**
 * Shared space-derived data for a community: the community's spaces plus the
 * per-space page/guest counts. Both the list (rows) and the fixed-header
 * controls need this; the underlying lists share cacheKeys so the data is
 * fetched once regardless of how many consumers mount.
 */
export function useCommunitySpaceData(communityId: MaybeRefOrGetter<string>) {
  const pages = useList<PageRecord>({
    doctype: 'GP Page',
    fields: ['project'],
    initialData: [],
    limit: 99999,
    cacheKey: 'space-page-counts',
  })

  const guestAccess = useList<GuestAccessRecord>({
    doctype: 'GP Guest Access',
    fields: ['project'],
    initialData: [],
    limit: 99999,
    cacheKey: 'space-guest-counts',
  })

  const communitySpaces = computed(() =>
    (spaces.data || []).filter((space) => space.team === toValue(communityId)),
  )

  const pagesCountBySpace = computed(() => {
    const counts: Record<string, number> = {}
    for (const page of pages.data || []) {
      if (!page.project) continue
      counts[page.project] = (counts[page.project] || 0) + 1
    }
    return counts
  })

  const guestsCountBySpace = computed(() => {
    const counts: Record<string, number> = {}
    for (const access of guestAccess.data || []) {
      if (!access.project) continue
      counts[access.project] = (counts[access.project] || 0) + 1
    }
    return counts
  })

  const getPagesCount = (spaceId: string) => pagesCountBySpace.value[spaceId] || 0
  const getGuestsCount = (spaceId: string) => guestsCountBySpace.value[spaceId] || 0

  const hasGuests = computed(() =>
    communitySpaces.value.some((space) => getGuestsCount(space.name) > 0),
  )

  return { communitySpaces, getPagesCount, getGuestsCount, hasGuests }
}
