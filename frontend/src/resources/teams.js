import { createListResource } from 'frappe-ui'

export let teams = createListResource({
  type: 'list',
  doctype: 'Team',
  fields: ['name', 'title', 'icon', 'modified', 'creation'],
  order_by: 'creation asc',
  cache: 'Sidebar Teams',
  transform(data) {
    return data.map((team) => {
      return {
        ...team,
        route: {
          name: 'TeamPageHome',
          params: { teamId: team.name },
        },
        open: false,
        projects: createProjectsResource(team.name),
      }
    })
  },
})
teams.reload()

function createProjectsResource(team) {
  return createListResource({
    doctype: 'Team Project',
    filters: { team },
    fields: ['name', 'title', 'icon', 'team'],
    order_by: 'creation asc',
    cache: ['Team Project List', team],
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
}
