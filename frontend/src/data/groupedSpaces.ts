import { computed, Ref } from 'vue'
import { spaces, Space } from './spaces'
import { teams, Team } from './teams'

type FilterFunction = (project: Space) => boolean | undefined
type GroupedSpaceItem = Team & { spaces: Space[] }
type Options = { filterFn?: FilterFunction }

export function useGroupedSpaces({ filterFn = (_p: Space) => true }: Options = {}): Ref<
  GroupedSpaceItem[]
> {
  return computed(() => {
    let groups: GroupedSpaceItem[] = []

    for (let team of teams.data || []) {
      let filteredSpaces = (spaces.data || []).filter((space: Space) => {
        return space.team === team.name && Boolean(filterFn(space))
      })
      if (filteredSpaces.length) {
        groups.push({
          ...team,
          spaces: filteredSpaces,
        })
      }
    }
    let ungrouped = (spaces.data || []).filter((space: Space) => {
      return !space.team && Boolean(filterFn(space))
    })
    if (ungrouped.length) {
      groups.push({
        name: 'Uncategorized',
        title: 'Uncategorized',
        spaces: ungrouped,
        is_private: 0,
        creation: '',
        modified: '',
      })
    }

    return groups
  })
}

export function useGroupedSpaceOptions({ filterFn = (_p: Space) => true }: Options = {}) {
  return computed(() => {
    let groupedSpaces = useGroupedSpaces({ filterFn }).value

    if (groupedSpaces.length === 1 && groupedSpaces[0].title == 'Uncategorized') {
      return groupedSpaces[0].spaces.map((space) => ({
        label: space.title,
        value: space.name,
        icon: space.icon,
      }))
    }

    return groupedSpaces.map((group) => {
      let options = group.spaces.map((space) => ({
        label: space.title,
        value: space.name,
        icon: space.icon,
      }))
      return {
        group: group.title,
        items: options,
        options,
      }
    })
  })
}

export const noCategories = computed(() => {
  let groups = useGroupedSpaces({ filterFn: (space) => !space.archived_at })
  return groups.value.length === 1 && groups.value[0].title == 'Uncategorized'
})
