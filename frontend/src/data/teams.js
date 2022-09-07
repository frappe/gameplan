import { createListResource } from 'frappe-ui'

export let teams = createListResource({
  type: 'list',
  doctype: 'Team',
  fields: ['name', 'title', 'icon', 'modified', 'creation'],
  order_by: 'title asc',
  cache: 'Teams',
  transform(data) {
    return data.map((team) => {
      return {
        ...team,
        route: {
          name: 'TeamPageHome',
          params: { teamId: team.name },
        },
        open: false,
        projects: [],
      }
    })
  },
})
teams.reload()
