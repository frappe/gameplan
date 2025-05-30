import { computed, ref, watch } from 'vue'
import { createDocumentResource, createListResource } from 'frappe-ui'

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
    { members: ['user'] },
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
  auto: false,
})

export function getTeamProjects(team) {
  return activeProjects.value.filter((project) => project.team === team) || []
}

export let activeProjects = computed(
  () => projects.data?.filter((project) => !project.archived_at) || [],
)

export let archivedProjects = computed(
  () => projects.data?.filter((project) => project.archived_at) || [],
)

export function getTeamArchivedProjects(team) {
  return archivedProjects.value.filter((project) => project.team === team) || []
}

export let getProject = (projectId) => {
  if (projectId == null) return null
  return projects.data.find((project) => project.name.toString() === projectId.toString())
}

export function useProject(projectId) {
  let documentResource = ref(null)

  watch(
    () => projectId.value,
    () => {
      documentResource.value = createDocumentResource({
        doctype: 'GP Project',
        name: projectId.value,
        whitelistedMethods: {
          moveToTeam: 'move_to_team',
          mergeWithProject: 'merge_with_project',
          archive: 'archive',
          unarchive: 'unarchive',
          inviteMembers: 'invite_members',
          inviteGuest: 'invite_guest',
          removeGuest: 'remove_guest',
          trackVisit: 'track_visit',
          follow: 'follow',
          unfollow: 'unfollow',
        },
      })
    },
    { immediate: true },
  )

  return documentResource
}
