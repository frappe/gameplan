import { computed, ComputedRef } from 'vue'
import { spaces } from '@/data/spaces'

let projectFormatters: Record<string, ComputedRef<string>> = {}

export function spaceTitle(
  project: string | number | null | undefined,
): ComputedRef<string> | string {
  if (project == null) {
    return ''
  }

  let projectId = project.toString()
  if (!projectFormatters[projectId]) {
    projectFormatters[projectId] = computed(() => {
      if (spaces.data && spaces.data.length > 0) {
        const foundSpace = spaces.data.find((space) => space.name.toString() === projectId)
        if (foundSpace) {
          return foundSpace.title
        }
      }
      return projectId
    })
  }
  return projectFormatters[projectId]
}
