import { computed, MaybeRefOrGetter, toValue } from 'vue'
import { useCall, useList, useDoctype, dialog } from 'frappe-ui'
import { GPProject, GPMember } from '@/types/doctypes'
import { getProjectUnreadCount, markSpacesAsRead } from './unreadCount'

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
    return spaces.data?.find((space) => space.name.toString() === _name?.toString()) ?? null
  })
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
