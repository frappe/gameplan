import { useDoctype } from 'frappe-ui'
import { GPProject } from '@/types/doctypes'
import { reactive } from 'vue'

interface ProjectUnreadCount {
  [spaceId: string]: number
}

interface ParticipatingUnreadCount {
  [team: string]: number
}

const unreadCounts = reactive<ProjectUnreadCount>({})
const participatingUnreadCounts = reactive<ParticipatingUnreadCount>({})

// All unread-count APIs live on the GP Unread Record controller, called via runMethod so we
// avoid hardcoded dotted module paths. Each `useDoctype` exposes ONE shared `runMethod`
// (a single useCall instance), and concurrent calls on it race on shared request state and
// cross-resolve. We therefore give each endpoint its own instance so they can safely overlap.
const unreadCountApi = useDoctype('GP Unread Record')
const participatingCountApi = useDoctype('GP Unread Record')
const markReadApi = useDoctype('GP Unread Record')

function loadProjectUnreadCounts(projects?: string[]) {
  return unreadCountApi.runMethod
    .submit({ method: 'get_unread_count', params: { projects } })
    .then((data: ProjectUnreadCount) => {
      // A full reload (no project filter) is authoritative: the backend omits spaces whose
      // count is now zero, so clear stale positives before applying the response — otherwise
      // a space that just dropped to zero keeps showing a phantom unread count.
      if (!projects) {
        for (const spaceId of Object.keys(unreadCounts)) {
          if (!(spaceId in data)) unreadCounts[spaceId] = 0
        }
      }
      for (const [spaceId, count] of Object.entries(data)) {
        // Counts cross the runMethod/JSON boundary as strings (MariaDB COUNT). Coerce to
        // Number here so summing them (e.g. per community) adds instead of concatenating.
        unreadCounts[spaceId] = Number(count) || 0
      }
      return data
    })
}

// load unread count for all projects once
loadProjectUnreadCounts()

export function getProjectUnreadCount(spaceId: string) {
  return unreadCounts[spaceId] ?? 0
}

// Two watchers (CommunityMenu + Discussions) and the post-mark refresh all call
// fetchParticipatingUnreadCount on the same shared runMethod instance, so their requests can
// overlap and resolve out of order — an older response would then write a pre-mark count back
// over a newer one. Track the latest request per team and apply only that response.
const participatingRequestSeq: Record<string, number> = {}

/** Fetch (and cache) the participating unread count for a community. */
export function fetchParticipatingUnreadCount(team: string) {
  const seq = (participatingRequestSeq[team] ?? 0) + 1
  participatingRequestSeq[team] = seq
  return participatingCountApi.runMethod
    .submit({ method: 'get_participating_unread_count', params: { team } })
    .then((count: number) => {
      // A newer fetch for this team superseded us — drop this stale response.
      if (participatingRequestSeq[team] !== seq) return participatingUnreadCounts[team] ?? 0
      participatingUnreadCounts[team] = Number(count) || 0
      return participatingUnreadCounts[team]
    })
}

export function getParticipatingUnreadCount(team: string) {
  return participatingUnreadCounts[team] ?? 0
}

/**
 * Mark discussions in a community as read.
 * @param before Optional `YYYY-MM-DD`; limits the action to discussions last active on or
 *   before that day. Omit to mark every unread discussion read.
 */
export function markCommunityAsRead(team: string, before?: string) {
  return markReadApi.runMethod
    .submit({ method: 'mark_all_as_read_for_team', params: { team, before } })
    .then(() => {
      // Reload the full map rather than only the marked projects: the AppRail sums unread
      // across every space it shows for a community, and that set can differ from the
      // backend's accessible-project list. A targeted refresh would leave the unmarked
      // spaces stale-high. A "before date" run may also leave newer discussions unread,
      // so recompute rather than assuming zero. These two run on separate API instances,
      // so concurrent refresh is safe.
      return Promise.all([loadProjectUnreadCounts(), fetchParticipatingUnreadCount(team)])
    })
}

const Project = useDoctype<GPProject>('GP Project')

export function markSpaceAsRead(spaceId: string) {
  return Project.runMethod
    .submit({
      method: 'mark_all_as_read',
      params: { spaces: [spaceId] },
    })
    .then(() => {
      return refreshUnreadCountForProjects([spaceId])
    })
}

export function markSpacesAsRead(spaceIds: string[]) {
  return Project.runMethod
    .submit({
      method: 'mark_all_as_read',
      params: {
        spaces: spaceIds,
      },
    })
    .then(() => {
      return refreshUnreadCountForProjects(spaceIds)
    })
}

export function refreshUnreadCountForProjects(projects: string[]) {
  return loadProjectUnreadCounts(projects)
}
