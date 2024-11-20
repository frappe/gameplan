import { createDocumentResource, createListResource, createResource } from 'frappe-ui'
import { computed } from 'vue'
import { getUser } from './users'

export let teams = createListResource({
  type: 'list',
  doctype: 'GP Team',
  fields: [
    'name',
    'title',
    'icon',
    'modified',
    'creation',
    'archived_at',
    'is_private',
    'is_default',
    { members: ['user'] },
  ],
  orderBy: 'title asc',
  cache: 'Teams',
  pageLength: 999,
  auto: true,
  onSuccess() {
    unreadItems.fetch()
  },
  transform(data) {
    return data.map((team) => {
      return {
        ...team,
        hasJoined: team.members.some((member) => member.user === getUser().name),
        route: {
          name: 'Team',
          params: { teamId: team.name },
        },
        projects: [],
      }
    })
  },
})

export let unreadItems = createResource({
  url: 'gameplan.api.get_unread_items',
  cache: 'UnreadItems',
})

export let activeTeams = computed(() => {
  return (teams.data || [])
    .filter((team) => !team.archived_at)
    .map((team) => {
      if (unreadItems.data) {
        team.unread = unreadItems.data[team.name] || 0
      }
      return team
    })
})

export let userSpaces = computed(() => {
  let user = getUser()
  return activeTeams.value.filter((team) => {
    let members = (team.members || []).map((member) => member.user)
    return members.includes(user.name)
  })
})

export let getTeam = (teamId) => {
  return teams.data.find((team) => team.name.toString() === teamId.toString())
}

export function useTeam(teamId: string) {
  let team = createDocumentResource({
    type: 'document',
    doctype: 'GP Team',
    name: teamId,
    realtime: true,
    whitelistedMethods: {
      join: 'join',
      addMembers: 'add_members',
      removeMember: 'remove_member',
      archive: 'archive',
      unarchive: 'unarchive',
    },
  })

  return team
}
