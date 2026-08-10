import { watch } from 'vue'
import { useDoc } from 'frappe-ui'
import type { GPUserProfile } from '@/types/doctypes'
import { people } from './people'
import { useUser, usersReady } from './users'
import { session } from './session'
import { isOnline, onReconnect } from './online'
import { prefetchProfileBento } from '@/components/ProfileBento/profileBentoSource'

/**
 * Warms every enabled member's offline data in the background so the People page and
 * any member's profile render offline even when neither was ever visited this session:
 * the People list itself, each member's `GP User Profile` doc (into the same `docStore`
 * entry `useDoc` reads on `PersonProfile.vue`), each member's bento cards, and each
 * member's avatar bytes (into the service worker's image cache).
 *
 * `useDoc` is the only supported way to warm `docStore` from outside frappe-ui - it isn't
 * exported from the package, only reached through `useDoc`'s own `afterFetch` hook (see
 * node_modules/frappe-ui/src/data-fetching/useDoc/useDoc.ts and ./docStore.ts). Calling it
 * here with the exact `doctype`/`name` PersonProfile.vue uses means a later visit finds
 * `docStore` already holding the doc (in memory, not just IDB) and skips straight to
 * rendering it while its own network refresh races in the background - the same
 * `staleOnError` fallback path an already-visited profile relies on offline.
 */

// A shared pool size (not one member at a time, not unbounded) so a workspace with a few
// hundred members doesn't flood the network, while still finishing in reasonable time.
const POOL_SIZE = 3
// Long enough that this never competes with the initial page load's own requests.
const INITIAL_DELAY_MS = 4000
const IDLE_TIMEOUT_MS = 10000

let running = false

/**
 * Idle-delayed kickoff so this never competes with the initial page load. Triggered by
 * the `session.isLoggedIn` watch below (covers both "already logged in at boot" and
 * "logged in mid-session without a page reload") rather than being called explicitly from
 * main.js, the same way data/discussions.ts and data/unreadCount.ts wire up their own
 * `onReconnect` callback at module scope - importing this module for its side effects is
 * enough (see main.js).
 */
export function scheduleOfflinePrefetch() {
  runWhenIdle(() => {
    if (session.isLoggedIn && isOnline.value) runOfflinePrefetch()
  })
}

watch(
  () => session.isLoggedIn,
  (loggedIn) => loggedIn && scheduleOfflinePrefetch(),
  {
    immediate: true,
  },
)

// A session that started offline never got its scheduled run in, and one that dropped
// mid-run may have only cached the first few members - both are exactly what a
// reconnect should retry. `onReconnect` is already debounced against flapping
// connectivity (data/online.ts), so this can't stampede on a flaky connection. The
// overlapping-run guard in `runOfflinePrefetch` covers this firing close to the initial
// idle-delayed run too.
onReconnect(() => {
  if (session.isLoggedIn) runOfflinePrefetch()
})

function runWhenIdle(fn: () => void) {
  if (typeof requestIdleCallback === 'function') {
    requestIdleCallback(() => fn(), { timeout: IDLE_TIMEOUT_MS })
  } else {
    setTimeout(fn, INITIAL_DELAY_MS)
  }
}

/**
 * Runs the full warm-up pass: reload the People list, then fan out per-member work
 * (profile doc, bento cards, avatar) through a small worker pool. Exported mainly so
 * tests/tools can trigger and await one pass directly instead of waiting on the idle
 * timer.
 */
export async function runOfflinePrefetch() {
  if (running || !isOnline.value) return
  running = true
  let counts = { members: 0, profiles: 0, bento: 0, avatars: 0 }
  try {
    console.debug('[offline-prefetch] start')
    await people.reload()

    // Avatar URLs come from the users store, not the People list - wait for its first
    // fetch to settle so an early run (or a slow `get_user_info`) doesn't skip every
    // avatar because `useUser` only has placeholders to hand back yet.
    await waitForUsersReady()

    let members = people.data || []
    counts.members = members.length

    let tasks = members.flatMap((member) => [
      () =>
        prefetchProfileDoc(member.name).then((ok) => {
          if (ok) counts.profiles++
        }),
      () =>
        prefetchProfileBento(member.name).then((ok) => {
          if (ok) counts.bento++
        }),
      () =>
        prefetchAvatar(useUser(member.user).user_image).then((ok) => {
          if (ok) counts.avatars++
        }),
    ])

    await runPool(tasks, POOL_SIZE)

    console.debug(
      `[offline-prefetch] done members=${counts.members} profiles=${counts.profiles} bento=${counts.bento} avatars=${counts.avatars}`,
    )
  } finally {
    running = false
  }
}

function waitForUsersReady(): Promise<void> {
  if (usersReady.value) return Promise.resolve()
  return new Promise((resolve) => {
    let stop = watch(usersReady, (ready) => {
      if (!ready) return
      stop()
      resolve()
    })
  })
}

/**
 * Pulls tasks off a shared queue with `poolSize` workers running concurrently, instead of
 * awaiting fixed-size batches - a worker that finishes early (a fast avatar load) picks up
 * the next task immediately rather than waiting on the slowest task in its batch. Checked
 * before every task, not just once: connectivity can drop midway through a run of a few
 * hundred members, and there is no point queuing more requests that will only fail once it
 * does.
 */
async function runPool(tasks: Array<() => Promise<void>>, poolSize: number) {
  let index = 0
  async function worker() {
    while (index < tasks.length) {
      if (!isOnline.value) return
      let task = tasks[index++]
      try {
        await task()
      } catch (error) {
        console.error('[offline-prefetch] task failed', error)
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(poolSize, tasks.length) }, worker))
}

/**
 * Fetches one member's profile doc and lets `useDoc`'s own `afterFetch` hook write it into
 * `docStore` (both the in-memory ref and IDB) - see the module doc comment above. `execute`
 * (aliased `fetch` on the returned object) never rejects; a network/HTTP failure resolves
 * to `null` instead, so this only reports success/failure for the debug counters, nothing
 * to catch.
 */
function prefetchProfileDoc(name: string): Promise<boolean> {
  let profileDoc = useDoc<GPUserProfile>({
    doctype: 'GP User Profile',
    name,
    immediate: false,
    staleOnError: true,
  })
  return profileDoc.fetch().then(Boolean)
}

/**
 * Loads an avatar through an `<img>` element rather than `fetch()` - the service worker
 * (gameplan/www/gameplan-sw.js) only caches requests whose `destination` is `image`
 * (`staleWhileRevalidate`), and a plain `fetch()` has `destination: ""`, which the worker
 * ignores. This has to actually load through the browser's image-fetch machinery, not
 * just hit the same URL.
 */
function prefetchAvatar(url: string | undefined): Promise<boolean> {
  if (!isSafeImageUrl(url)) return Promise.resolve(false)
  return new Promise((resolve) => {
    let img = new Image()
    img.onload = () => resolve(true)
    img.onerror = () => resolve(false)
    img.src = url
  })
}

// Same-origin only: the service worker ignores cross-origin requests outright
// (`url.origin !== self.location.origin` in gameplan-sw.js), and there is no reason to
// send a user's avatar URL to a third-party origin from a background prefetcher anyway.
function isSafeImageUrl(url: string | undefined): url is string {
  if (!url) return false
  if (url.startsWith('/') && !url.startsWith('//')) return true
  try {
    let parsed = new URL(url, window.location.origin)
    return (
      (parsed.protocol === 'http:' || parsed.protocol === 'https:') &&
      parsed.origin === window.location.origin
    )
  } catch {
    return false
  }
}
