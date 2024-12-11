import { computed, Ref } from 'vue'
import { projects } from './projects'
import { activeTeams } from './teams'
import { GPProject, GPTeam } from './types'

type FilterFunction = (project: GPProject) => boolean
type GroupedSpaceItem = GPTeam & { spaces: GPProject[] }
type Options = { filterFn?: FilterFunction }

export function useGroupedSpaces({ filterFn = (_p: GPProject) => true }: Options = {}): Ref<
  GroupedSpaceItem[]
> {
  return computed(() => {
    let groups: GroupedSpaceItem[] = []

    for (let team of activeTeams.value as GPTeam[]) {
      let spaces = (projects.data || []).filter((project: GPProject) => {
        return project.team === team.name && filterFn(project)
      })
      if (spaces.length) {
        groups.push({
          ...team,
          spaces,
        })
      }
    }
    let ungrouped = (projects.data || []).filter((project: GPProject) => {
      return !project.team && filterFn(project)
    })
    if (ungrouped.length) {
      groups.push({
        name: 'Uncategorized',
        title: 'Uncategorized',
        spaces: ungrouped,
      })
    }

    return groups
  })
}
