import { createListResource } from 'frappe-ui'

export let teams = createListResource({
  type: 'list',
  doctype: 'Team',
  fields: ['name', 'title', 'icon', 'modified', 'creation'],
  order_by: 'title asc',
  cache: 'Teams',
  limit: 999,
  transform(data) {
    return data.map((team) => {
      return {
        ...team,
        route: {
          name: 'Team',
          params: { teamId: team.name },
        },
        class($route, link) {
          if (
            [
              'Team',
              'TeamHome',
              'TeamOverview',
              'TeamProjects',
            ].includes($route.name) &&
            $route.params.teamId === link.route.params.teamId
          ) {
            return 'bg-white shadow-sm text-gray-900'
          }
          return 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
        },
        open: false,
        projects: [],
      }
    })
  },
})
teams.reload()
