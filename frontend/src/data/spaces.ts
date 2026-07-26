import { computed, MaybeRefOrGetter, toValue } from 'vue'
import { useCall, useList, useDoc, useDoctype, dialog } from 'frappe-ui'
import { GPProject, GPMember } from '@/types/doctypes'
import { getProjectUnreadCount, markSpacesAsRead } from './unreadCount'
import { useSessionUser } from './users'
import { canManageSpace } from '@/utils/permissions'
import { readOnlyMode } from './readOnlyMode'

interface Member extends Pick<GPMember, 'user'> {}

export interface Space
  extends Pick<
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
  cacheKey: 'spaces',
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
 * destructive/admin actions (manage access, archive, unarchive).
 */
export function useSpacePermissions(spaceId: MaybeRefOrGetter<string | undefined>) {
  const space = useSpace(spaceId)
  const sessionUser = useSessionUser()
  const isArchived = computed(() => Boolean(space.value?.archived_at))
  const canEditSpace = computed(() => !readOnlyMode && !isArchived.value)
  const canManageAccess = computed(() => !readOnlyMode && canManageSpace(space.value, sessionUser))
  return { space, isArchived, canEditSpace, canManageAccess }
}

export function getSpace(name: string) {
  return spaces.data?.find((space) => space.name.toString() === name.toString()) ?? null
}

export const joinedSpaces = useCall<string[]>({
  url: '/api/v2/method/GP Project/get_joined_spaces',
  cacheKey: 'joinedSpaces',
  initialData: [],
})

export function hasJoined(spaceId: MaybeRefOrGetter<string>) {
  return joinedSpaces.data?.includes(toValue(spaceId))
}

export function getSpaceUnreadCount(spaceId: string) {
  return getProjectUnreadCount(spaceId)
}

export function trackSpaceVisit(spaceId: string) {
  return spaceDoctype.runMethod.submit({
    method: 'track_visits',
    params: { spaces: [spaceId] },
  })
}

export function useSpaceFollowing(spaceId: MaybeRefOrGetter<string>) {
  const space = useDoc<GPProject>({
    doctype: 'GP Project',
    name: spaceId,
  })
  const isFollowed = computed(() => Boolean(space.doc?.is_followed))

  async function follow() {
    await spaceDoctype.runMethod.submit({
      method: 'follow_spaces',
      params: { spaces: [toValue(spaceId)] },
    })
    await space.reload()
  }

  async function unfollow() {
    await spaceDoctype.runMethod.submit({
      method: 'unfollow_spaces',
      params: { spaces: [toValue(spaceId)] },
    })
    await space.reload()
  }

  return { isFollowed, follow, unfollow }
}

const spaceDoctype = useDoctype<GPProject>('GP Project')

export function joinSpace(space: Space) {
  return spaceDoctype.runDocMethod
    .submit({
      method: 'join',
      name: space.name,
    })
    .then(() => {
      joinedSpaces.reload()
    })
}

export function joinSpaces(spaceIds: string[]) {
  return spaceDoctype.runMethod
    .submit({
      method: 'join_spaces',
      params: {
        spaces: spaceIds,
      },
    })
    .then(() => {
      joinedSpaces.reload()
    })
}

export function leaveSpace(space: Space) {
  return spaceDoctype.runDocMethod
    .submit({
      method: 'leave',
      name: space.name,
    })
    .then(() => {
      joinedSpaces.reload()
    })
}

export function leaveSpaces(spaceIds: string[]) {
  return spaceDoctype.runMethod
    .submit({
      method: 'leave_spaces',
      params: {
        spaces: spaceIds,
      },
    })
    .then(() => {
      joinedSpaces.reload()
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
