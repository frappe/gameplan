import { computed, MaybeRefOrGetter, toValue } from 'vue'
import { dialog, useDoctype, useList } from 'frappe-ui'
import { GPTeam, GPMember } from '@/types/doctypes'
import { communityOrder } from './communityOrder'
import { useSessionUser } from './users'

export interface CommunityMember extends Pick<GPMember, 'user' | 'is_admin'> {
  user: string
  is_admin?: 0 | 1
}

export interface Community extends Pick<
  GPTeam,
  'name' | 'title' | 'icon' | 'image' | 'modified' | 'creation' | 'archived_at' | 'is_private'
> {
  members: CommunityMember[]
}

export let communities = useList<Community>({
  doctype: 'GP Team',
  fields: [
    'name',
    'title',
    'icon',
    'image',
    'modified',
    'creation',
    'archived_at',
    'is_private',
    { members: ['user', 'is_admin'] },
  ],
  orderBy: 'title asc',
  initialData: [],
  cacheKey: ['Communities', 'with-image'],
  limit: 999,
  transform(data) {
    for (let community of data) {
      community.name = community.name.toString()
    }
    return data
  },
  immediate: true,
})

export let availableCommunities = computed(() => {
  return (communities.data || []).filter((community) => !community.archived_at)
})

export let activeCommunities = computed(() => {
  return sortCommunitiesByUserOrder(availableCommunities.value.filter(isCommunityJoined))
})

export let useCommunity = (communityId: MaybeRefOrGetter<string | undefined>) => {
  return computed(() => {
    let _communityId = toValue(communityId)
    if (!_communityId) {
      return null
    }
    return getCommunity(_communityId)
  })
}

export let getCommunity = (communityId: string) => {
  return (communities.data || []).find(
    (community) => community.name.toString() === communityId.toString(),
  )
}

export let getActiveCommunity = (communityId: string) => {
  return activeCommunities.value.find(
    (community) => community.name.toString() === communityId.toString(),
  )
}

const communityDoctype = useDoctype<GPTeam>('GP Team')

/**
 * Join a community. Membership is what lists a community and its public spaces in
 * the sidebar, so this is how a member gets to a public community they can already
 * read. Private communities are invite only and the backend rejects them.
 */
export function joinCommunity(community: Community) {
  return communityDoctype.runMethod
    .submit({ method: 'join_team', params: { team: community.name } })
    .then(() => communities.reload())
}

export function leaveCommunity(community: Community) {
  return communityDoctype.runMethod
    .submit({ method: 'leave_team', params: { team: community.name } })
    .then(() => communities.reload())
}

/**
 * Ask before leaving. A public community is one click away again, but a private one's
 * view permission *is* its membership (backend `can_view_community`), so leaving hides
 * it and its Join action for good. Mirrors `confirmLeaveSpace`.
 *
 * The dialog holds its loading state until the call settles and renders a rejection
 * inline, which is where the "last admin cannot leave" message lands.
 */
export function confirmLeaveCommunity(community: Community) {
  dialog.confirm({
    title: `Leave "${community.title}"?`,
    message: community.is_private
      ? "This community is private. You won't be able to rejoin unless a member adds you back."
      : 'Its spaces leave your sidebar. You can rejoin at any time.',
    confirmLabel: 'Leave',
    onConfirm: () => leaveCommunity(community),
  })
}

export function isCommunityJoined(community: Community) {
  let user = getSessionUserFromCookie()
  if (!user) return false
  // Guests never become community members; the backend only returns communities that
  // hold a space they've been granted, so every fetched community is one they should
  // see in the shell.
  if (useSessionUser().isGuest) return true
  return Boolean(community.members?.some((member) => member.user === user))
}

function sortCommunitiesByUserOrder(communities: Community[]) {
  let orderByName = new Map(communityOrder.value.map((name, index) => [name, index]))
  return [...communities].sort((left, right) => {
    let leftOrder = orderByName.get(left.name) ?? Number.MAX_SAFE_INTEGER
    let rightOrder = orderByName.get(right.name) ?? Number.MAX_SAFE_INTEGER

    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder
    }

    return left.title.localeCompare(right.title)
  })
}

function getSessionUserFromCookie() {
  let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  let user = cookies.get('user_id')
  return user === 'Guest' ? null : user
}
