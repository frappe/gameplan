import { computed, MaybeRefOrGetter, toValue } from 'vue'
import { useCall, useList } from 'frappe-ui/src/data-fetching'
import { GPProject, GPMember } from '@/types/doctypes'

interface Member extends Pick<GPMember, 'user' | 'notify_new_posts' | 'notify_new_comments'> {}

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
    { members: ['user', 'notify_new_posts', 'notify_new_comments'] },
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

export function useSpace(name: MaybeRefOrGetter<string>) {
  return computed(() => {
    let _name = toValue(name)
    return spaces.data?.find((space) => space.name.toString() === _name?.toString()) ?? null
  })
}

export const joinedSpaces = useCall<string[]>({
  url: '/api/v2/method/GP Project/get_joined_spaces',
  cacheKey: 'joinedSpaces',
  initialData: [],
})
