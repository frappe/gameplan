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
  return projects.data?.filter((project) => project.team === team) || []
}
