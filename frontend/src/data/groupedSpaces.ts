import { computed, Ref } from 'vue'
import { spaces, Space } from './spaces'
import { activeTeams, Team } from './teams'

type FilterFunction = (project: Space) => boolean
type GroupedSpaceItem = Team & { spaces: Space[] }
type Options = { filterFn?: FilterFunction }

export function useGroupedSpaces({ filterFn = (_p: Space) => true }: Options = {}): Ref<
  GroupedSpaceItem[]
> {
  return computed(() => {
    let groups: GroupedSpaceItem[] = []

    for (let team of activeTeams.value) {
      let filteredSpaces = (spaces.data || []).filter((space: Space) => {
        return space.team === team.name && filterFn(space)
      })
      if (filteredSpaces.length) {
        groups.push({
          ...team,
          spaces: filteredSpaces,
        })
      }
    }
    let ungrouped = (spaces.data || []).filter((space: Space) => {
      return !space.team && filterFn(space)
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
