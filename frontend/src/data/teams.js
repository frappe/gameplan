import { createListResource } from 'frappe-ui'

export let teams = createListResource({
  type: 'list',
  doctype: 'Team',
  fields: ['name', 'title', 'icon', 'modified', 'creation', 'archived_at'],
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
        open: false,
        projects: [],
      }
    })
  },
})
teams.reload()
