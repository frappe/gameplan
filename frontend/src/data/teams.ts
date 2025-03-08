import { computed } from 'vue'
import { useList } from 'frappe-ui/src/data-fetching'
import { GPTeam } from '@/types/doctypes'

export interface Team
  extends Pick<
    GPTeam,
    'name' | 'title' | 'icon' | 'modified' | 'creation' | 'archived_at' | 'is_private'
  > {}

export let teams = useList<Team>({
  doctype: 'GP Team',
  fields: ['name', 'title', 'icon', 'modified', 'creation', 'archived_at', 'is_private'],
  orderBy: 'title asc',
  initialData: [],
  cacheKey: 'Teams',
  limit: 999,
  immediate: true,
})

export let activeTeams = computed(() => {
  return (teams.data || []).filter((team) => !team.archived_at)
})

export let getTeam = (teamId: string) => {
  return (teams.data || []).find((team) => team.name.toString() === teamId.toString())
}
