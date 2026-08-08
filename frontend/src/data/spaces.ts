import { computed, MaybeRefOrGetter, toValue } from 'vue'
import { useCall, useList, useDoctype, dialog } from 'frappe-ui'
import { GPProject, GPMember } from '@/types/doctypes'
import { getProjectUnreadCount, markSpacesAsRead } from './unreadCount'
import { useSessionUser } from './users'
import { canManageSpace, isGuest } from '@/utils/permissions'
import { readOnlyMode } from './readOnlyMode'
import { session } from './session'

interface Member extends Pick<GPMember, 'user'> {}

export interface Space extends Pick<
  GPProject,
  | 'name'
  | 'title'
  | 'icon'
  | 'team'
  | 'archived_at'
  | 'is_private'
  | 'modified'
  | 'tasks_count'
  | 'discussions_count'
> {
  team_title: string
  members: Member[]
}

export let spaces = useList<Space>({
  doctype: 'GP Project',
  fields: [
    'name',
    'title',
    'icon',
    'team',
    'archived_at',
    'is_private',
    'modified',
    'tasks_count',
    'discussions_count',
    'team.title as team_title',
    { members: ['user'] },
  ],
  initialData: [],
  orderBy: 'title asc',
  limit: 99999,
  // Scoped to the session user so a second account on the same browser can't read the
  // first account's cached space list while offline (review finding from PR #516).
  cacheKey: ['spaces', session.user],
  staleOnError: true,
  transform(data) {
    for (let space of data) {
      space.name = space.name.toString()
    }
    return data
  },
  immediate: true,
})

export function useSpace(name: MaybeRefOrGetter<string | undefined>) {
  return computed(() => {
    let _name = toValue(name)
    if (!_name) return null
    return getSpace(_name)
  })
}

/**
 * Shared gates for the space-action menus (the options dropdown and the discussions-header
 * menu). Kept in one place so a permission-rule change can't leave the two menus disagreeing
 * about who may edit vs. manage a space. `canEditSpace` covers non-destructive edits on a live
 * space; `canManageAccess` mirrors the backend `can_manage_space` and additionally gates the
 * destructive/admin actions (manage access, archive, unarchive); `canChangeMembership` gates
 * joining and leaving, and `canMoveDiscussions` the bulk move. The last two are neither edits
 * nor admin actions, and both are closed to guests.
 *
 * They are kept off `canEditSpace` because a guest may edit content in a space they were
 * granted while being unable to do either of these. For membership, `get_joined_spaces` unions
 * GP Member rows with GP Guest Access rows, so a granted space looks "joined" to a guest while
 * `leave_spaces` only touches member rows; for the move, the backend refuses it outright.
 * Either way, offering the control produces a button that can never do anything.
 */
export function useSpacePermissions(spaceId: MaybeRefOrGetter<string | undefined>) {
  const space = useSpace(spaceId)
  const sessionUser = useSessionUser()
  const isArchived = computed(() => Boolean(space.value?.archived_at))
  const isGuestUser = computed(() => isGuest(sessionUser))
  const canEditSpace = computed(() => !readOnlyMode && !isArchived.value)
  const canManageAccess = computed(() => !readOnlyMode && canManageSpace(space.value, sessionUser))
  const canChangeMembership = computed(() => canEditSpace.value && !isGuestUser.value)
  const canMoveDiscussions = computed(() => canEditSpace.value && !isGuestUser.value)
  return {
    space,
    isArchived,
    canEditSpace,
    canManageAccess,
    canChangeMembership,
    canMoveDiscussions,
  }
}

/**
 * Can new content (a discussion, page or task) be created in this space? The backend refuses
 * posts in an archived space, and read-only mode blocks every write, so both are filtered out
 * before a space is ever offered as a target.
 *
 * Guests are out everywhere: backend `can_create_content` lets a guest create only a
 * `GP Comment` or a `GP Poll`, so a discussion, page or task is refused in every space,
 * including the ones they were granted. Being in the spaces list is not enough on its own —
 * that list is scoped to what a user may *read*, and a guest can read plenty they cannot post
 * in. For everyone else membership is not part of the test, because read access and post
 * access are the same thing.
 */
export function canPostInSpace(space: Space | null | undefined) {
  if (!space || readOnlyMode || space.archived_at) return false
  return !isGuest(useSessionUser())
}

export function getSpace(name: string) {
  return spaces.data?.find((space) => space.name.toString() === name.toString()) ?? null
}

export const joinedSpaces = useCall<string[]>({
  url: '/api/v2/method/GP Project/get_joined_spaces',
  cacheKey: ['joinedSpaces', session.user],
  staleOnError: true,
  initialData: [],
})

export function hasJoined(spaceId: MaybeRefOrGetter<string>) {
  return joinedSpaces.data?.includes(toValue(spaceId))
}

export function getSpaceUnreadCount(spaceId: string) {
  return getProjectUnreadCount(spaceId)
}

export function trackSpaceVisit(spaceId: string) {
  return spaceVisitApi.runMethod.submit({
    method: 'track_visits',
    params: { spaces: [spaceId] },
  })
}

const spaceDoctype = useDoctype<GPProject>('GP Project')
// Mount-time visit tracking can overlap a menu action. Keep it off spaceDoctype's single
// shared runMethod request so the two calls cannot cross-resolve each other's state.
const spaceVisitApi = useDoctype<GPProject>('GP Project')

export function joinSpace(space: Space) {
  return spaceDoctype.runMethod
    .submit({
      method: 'join_spaces',
      params: { spaces: [space.name] },
    })
    .then(() => {
      joinedSpaces.reload()
    })
}

export function leaveSpace(space: Space) {
  return spaceDoctype.runMethod
    .submit({
      method: 'leave_spaces',
      params: { spaces: [space.name] },
    })
    .then(() => {
      joinedSpaces.reload()
    })
}

/**
 * Ask before leaving. Leaving a public space is reversible from the space itself, but a
 * private space's view permission *is* its membership (backend `can_view_space`), so the
 * moment you leave you can no longer see the space — or the Join action on it. Getting back
 * in needs another member (or a global admin) to add you, which is worth a warning up front.
 */
export function confirmLeaveSpace(space: Space) {
  dialog.confirm({
    title: `Leave "${space.title}"?`,
    message: space.is_private
      ? "This space is private. You won't be able to rejoin unless a member adds you back."
      : 'You can rejoin at any time.',
    confirmLabel: 'Leave',
    onConfirm: () => leaveSpace(space),
  })
}

export function archiveSpace(space: Space) {
  dialog.confirm({
    title: 'Archive space',
    message:
      'You cannot create new discussions, pages or tasks in an archived space. It will remain read-only. You can unarchive it again at any time.',
    confirmLabel: 'Archive',
    onConfirm: () => spaceDoctype.runDocMethod.submit({ method: 'archive', name: space.name }),
  })
}

export function unarchiveSpace(space: Space) {
  return spaceDoctype.runDocMethod.submit({
    method: 'unarchive',
    name: space.name,
  })
}

export function markAllAsRead(spaceIds: string[], groupTitle: string) {
  dialog.confirm({
    title: 'Mark all as read',
    message: `Are you sure you want to mark all discussions in ${groupTitle} as read? This action cannot be undone.`,
    confirmLabel: 'Mark all as read',
    onConfirm: () => markSpacesAsRead(spaceIds),
  })
}

export function isDocMethodLoading(docname: string, method: string) {
  return spaceDoctype.runDocMethod.isLoading(docname, method)
}

export function isMethodLoading(method: string) {
  return spaceDoctype.runMethod.isLoading(method)
}
