import { computed, Ref } from 'vue'
import { spaces, Space } from './spaces'
import { communities, Community } from './communities'

type FilterFunction = (project: Space) => boolean | undefined
export type GroupedSpaceItem = Community & { spaces: Space[] }
type Options = { filterFn?: FilterFunction }

// Spaces with no community are collected under a synthetic group that carries this as
// both its name and title. It is not a real community, so anything reading the owning
// community off a group has to treat it as "none".
const UNCATEGORIZED = 'Uncategorized'

export function useGroupedSpaces({ filterFn = (_p: Space) => true }: Options = {}): Ref<
  GroupedSpaceItem[]
> {
  return computed(() => {
    let groups: GroupedSpaceItem[] = []

    for (let community of communities.data || []) {
      let filteredSpaces = (spaces.data || []).filter((space: Space) => {
        return space.team === community.name && Boolean(filterFn(space))
      })
      if (filteredSpaces.length) {
        groups.push({
          ...community,
          spaces: filteredSpaces,
        })
      }
    }
    let ungrouped = (spaces.data || []).filter((space: Space) => {
      return !space.team && Boolean(filterFn(space))
    })
    if (ungrouped.length) {
      groups.push({
        name: UNCATEGORIZED,
        title: UNCATEGORIZED,
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

    if (groupedSpaces.length === 1 && groupedSpaces[0].title == UNCATEGORIZED) {
      return groupedSpaces[0].spaces.map((space) => ({
        label: space.title,
        value: space.name,
        icon: space.icon,
        community: null,
      }))
    }

    return groupedSpaces.map((group) => ({
      group: group.title,
      options: group.spaces.map((space) => ({
        label: space.title,
        value: space.name,
        icon: space.icon,
        // Title of the community that owns the space, for consumers that show the pair
        // outside the grouped list, where the group header is not there to name it.
        community: group.name === UNCATEGORIZED ? null : group.title,
      })),
    }))
  })
}
