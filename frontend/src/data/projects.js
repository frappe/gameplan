import { computed } from 'vue'
import { createListResource } from 'frappe-ui'

export let projects = createListResource({
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
  ],
  orderBy: 'title asc',
  pageLength: 999,
  cache: 'Projects',
  transform(projects) {
    return projects.map((project) => {
      project.route = {
        name: 'Project',
        params: {
          teamId: project.team,
          projectId: project.name,
        },
      }
      return project
    })
  },
  auto: true,
})

export function getTeamProjects(team) {
  return activeProjects.value.filter((project) => project.team === team) || []
}

export let activeProjects = computed(
  () => projects.data?.filter((project) => !project.archived_at) || []
)

export let getProject = (projectId) => {
  return projects.data.find(
    (project) => project.name.toString() === projectId.toString()
  )
}
