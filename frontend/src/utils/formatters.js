import { projects } from '@/data/projects'
import { computed } from 'vue'

let projectFormatters = {}
export function projectTitle(project) {
  if (project == null) {
    return ''
  }

  let projectId = project.toString()
  if (!projectFormatters[projectId]) {
    projectFormatters[projectId] = computed(() => {
      if (projects.data.length > 0) {
        const project = projects.data.find(
          (p) => p.name.toString() === projectId,
        )
        if (project) {
          return project.title
        }
      }
      return projectId
    })
  }
  return projectFormatters[projectId]
}
