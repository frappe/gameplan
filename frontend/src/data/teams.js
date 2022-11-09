import { createListResource, createResource } from 'frappe-ui'
import { computed } from 'vue'

export let teams = createListResource({
  type: 'list',
  doctype: 'Team',
  fields: ['name', 'title', 'icon', 'modified', 'creation', 'archived_at'],
  order_by: 'title asc',
  cache: 'Teams',
  limit: 999,
  onSuccess() {
    unreadItems.fetch()
  },
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

export let unreadItems = createResource({
  method: 'gameplan.api.get_unread_items',
  cache: 'UnreadItems',
  onSuccess(data) {
    for (let team of teams.data) {
      team.unread = data[team.name] || 0
    }
  },
})

export let activeTeams = computed(() => {
  return (teams.data || []).filter((team) => !team.archived_at)
})
