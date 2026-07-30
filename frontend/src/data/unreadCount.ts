import { useDoctype } from 'frappe-ui'
import { GPProject } from '@/types/doctypes'
import { reactive } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { onSocketEvent } from '@/socket'

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
// (a single useCall instance), so we give each endpoint its own instance and queue submissions
// within it — see `queued` below for why overlapping on one instance is unsafe.
const unreadCountApi = useDoctype('GP Unread Record')
const participatingCountApi = useDoctype('GP Unread Record')
const markReadApi = useDoctype('GP Unread Record')

const submitQueues = new WeakMap<object, Promise<unknown>>()

/**
 * Run `submit` only once every earlier submission on the same API instance has settled.
 *
 * A single useCall instance cannot serve two calls at once. VueUse's fetch aborts the in-flight
 * request when a second submit starts, and useCall resolves *every* submit from the same shared
 * `data` ref — so the aborted caller resolves with whatever `data` happens to hold, which is the
 * previous response rather than its own. Its refresh is silently dropped and a stale snapshot
 * re-applied on top.
 *
 * Overlap is routine now that the server pushes: opening a discussion fires a targeted refresh
 * from `trackVisit`'s callback at roughly the same moment the push fires a full reload, and one
 * live signal fans out a `fetchParticipatingUnreadCount` per cached community at once — where
 * the dropped-response effect is worst, since those calls differ only by subject and one
 * community's count then lands under another's key.
 *
 * The real fix belongs in frappe-ui's useCall, which should resolve each submit with its own
 * response; until then, one request in flight per instance keeps the counts honest.
 */
function queued<T>(api: object, submit: () => Promise<T>): Promise<T> {
  const run = (submitQueues.get(api) ?? Promise.resolve()).then(submit, submit)
  submitQueues.set(
    api,
    run.catch(() => {}),
  )
  return run
}

function loadProjectUnreadCounts(projects?: string[]) {
  return queued(unreadCountApi, () =>
    unreadCountApi.runMethod
      .submit({
        method: 'get_unread_count',
        // Autoincremented Space names can arrive on a freshly loaded document as
        // numbers, while the whitelisted endpoint deliberately accepts list[str].
        params: { projects: projects?.map(String) },
      })
      .then((data: ProjectUnreadCount | null) => {
        const counts = data ?? {}
        // A full reload (no project filter) is authoritative: the backend omits spaces whose
        // count is now zero, so clear stale positives before applying the response — otherwise
        // a space that just dropped to zero keeps showing a phantom unread count.
        if (!projects) {
          for (const spaceId of Object.keys(unreadCounts)) {
            if (!(spaceId in counts)) unreadCounts[spaceId] = 0
          }
        }
        for (const [spaceId, count] of Object.entries(counts)) {
          // Counts cross the runMethod/JSON boundary as strings (MariaDB COUNT). Coerce to
          // Number here so summing them (e.g. per community) adds instead of concatenating.
          unreadCounts[spaceId] = Number(count) || 0
        }
        return counts
      }),
  )
}

// load unread count for all projects once
loadProjectUnreadCounts()

export function getProjectUnreadCount(spaceId: string) {
  return unreadCounts[spaceId] ?? 0
}

/**
 * Fetch (and cache) the participating unread count for a community.
 *
 * Two watchers (CommunityMenu + Discussions), the post-mark refresh and the live refresh below
 * all call this, and the live refresh fans out one call per cached community at once. Queueing
 * keeps them from cross-resolving on the shared instance — without it, every community would
 * end up displaying whichever count answered last.
 */
export function fetchParticipatingUnreadCount(team: string) {
  return queued(participatingCountApi, () =>
    participatingCountApi.runMethod
      .submit({ method: 'get_participating_unread_count', params: { team } })
      .then((count: number) => {
        participatingUnreadCounts[team] = Number(count) || 0
        return participatingUnreadCounts[team]
      }),
  )
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
      params: { spaces: [String(spaceId)] },
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
        spaces: spaceIds.map(String),
      },
    })
    .then(() => {
      return refreshUnreadCountForProjects(spaceIds)
    })
}

export function refreshUnreadCountForProjects(projects: string[]) {
  return loadProjectUnreadCounts(projects)
}

// The backend signals this after any create/mark-read change to GP Unread Record, so other tabs
// (and spaces you're not currently viewing) pick up the change without a manual reload.
// Debounced because one action fans out several signals — posting creates records for every
// recipient and marks the thread read for the author — and each one costs a full map fetch plus
// a request per cached community.
onSocketEvent(
  'gameplan:unread_counts_changed',
  useDebounceFn(() => {
    // Nothing awaits these; swallow failures so a dropped request doesn't surface as an
    // unhandled rejection. The next signal (or a page load) refetches anyway.
    Promise.allSettled([
      loadProjectUnreadCounts(),
      ...Object.keys(participatingUnreadCounts).map((team) => fetchParticipatingUnreadCount(team)),
    ])
  }, 500),
)
