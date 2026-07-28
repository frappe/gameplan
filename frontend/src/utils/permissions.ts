import type { Community } from '@/data/communities'
import { getCommunity } from '@/data/communities'
import type { Space } from '@/data/spaces'

type PermissionUser = {
  name?: string | null
  role?: string
}

export function canManageCommunity(community: Community | null | undefined, user: PermissionUser) {
  if (!community || !user.name) return false
  return isGlobalAdmin(user) || isCommunityAdmin(community, user.name)
}

export function getManageableCommunities(communities: Community[], user: PermissionUser) {
  if (isGlobalAdmin(user)) return communities
  return communities.filter((community) => canManageCommunity(community, user))
}

export function isCommunityAdmin(community: Community | null | undefined, user: string) {
  return Boolean(community?.members?.some((member) => member.user === user && member.is_admin))
}

export function isGlobalAdmin(user: PermissionUser) {
  return user.name === 'Administrator' || user.role === 'Gameplan Admin'
}

export function isGuest(user: PermissionUser) {
  return user.role === 'Gameplan Guest'
}

/**
 * Mirror of backend `can_manage_space`: global admins can manage any space,
 * private-space members can manage their own space, and public spaces are
 * managed by community admins. Derived from already-fetched space/community
 * membership, so it adds no network round-trip.
 */
export function canManageSpace(space: Space | null | undefined, user: PermissionUser) {
  if (!space || !user.name) return false
  if (isGlobalAdmin(user)) return true
  if (space.is_private) {
    return Boolean(space.members?.some((member) => member.user === user.name))
  }
  return isCommunityAdmin(getCommunity(space.team), user.name)
}

/** Guests can never invite; otherwise invite rights follow space management. */
export function canInviteGuests(space: Space | null | undefined, user: PermissionUser) {
  if (isGuest(user)) return false
  return canManageSpace(space, user)
}

type ContentDoc = { owner?: string | null } | null | undefined

/**
 * Mirror of backend `can_delete_content` (gameplan/permissions.py): global admins
 * always; the content owner (members and guests alike may delete what they
 * authored); guests have no further delete rights; otherwise a community admin of
 * the content's space's community. Gameplan is permissive — members create and edit
 * freely (edits are transparent via revisions) — so DELETE-others is the one content
 * action that stays gated.
 *
 * `space` is the content's space (GP Project); pass null/undefined for personal
 * content with no space, where only the owner or a global admin can delete.
 */
export function canDeleteContent(
  content: ContentDoc,
  space: Space | null | undefined,
  user: PermissionUser,
) {
  if (!content || !user.name) return false
  if (isGlobalAdmin(user)) return true
  if (content.owner === user.name) return true
  if (isGuest(user)) return false
  if (!space) return false
  return isCommunityAdmin(getCommunity(space.team), user.name)
}

/**
 * Mirror of backend `can_edit_content` (gameplan/permissions.py): global admins
 * always; a guest only on content they authored (guests are participants but may
 * edit just their own posts/comments); any member on content inside a space
 * (Gameplan is community-driven, so space content is member-editable and edits
 * are transparent via revisions); personal content with no space only by its
 * owner. Callers render this only for content the user can already view, which
 * is the backend's view-gate precondition.
 *
 * `space` is the content's space (GP Project); pass null/undefined for personal
 * content with no space.
 */
export function canEditContent(
  content: ContentDoc,
  space: Space | null | undefined,
  user: PermissionUser,
) {
  if (!content || !user.name) return false
  if (isGlobalAdmin(user)) return true
  if (isGuest(user)) return content.owner === user.name
  if (space) return true
  return content.owner === user.name
}
