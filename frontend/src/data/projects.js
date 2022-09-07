import { createListResource } from 'frappe-ui'

export let projects = createListResource({
  doctype: 'Team Project',
  fields: ['name', 'title', 'icon', 'team'],
  order_by: 'title asc',
  limit: 999,
  cache: 'Projects',
  transform(projects) {
    return projects.map((project) => {
      project.route = {
        name: 'ProjectDetailOverview',
        params: {
          teamId: project.team,
          projectId: project.name,
        },
      }
      return project
    })
  },
})

export function getTeamProjects(team) {
  return projects.data?.filter((project) => project.team === team) || []
}
projects.reload()
