import { clear as clearIdbKeyval } from 'idb-keyval'
import { toast } from 'frappe-ui'
import { clearDraftStore } from '@/data/draftStore'
import { onReconnect } from '@/data/online'

const SERVICE_WORKER_URL = '/gameplan-sw.js'
const SERVICE_WORKER_SCOPE = '/g'
const CACHE_URLS_MESSAGE = 'CACHE_URLS'
const CLEAR_USER_CACHES_MESSAGE = 'CLEAR_USER_CACHES'
const WARM_SHELL_CACHE_MESSAGE = 'WARM_SHELL_CACHE'
const SKIP_WAITING_MESSAGE = 'SKIP_WAITING'
const LAST_SEEN_USER_STORAGE_KEY = 'gameplan:last-seen-user'
// Must match gameplan-sw.js's own CACHE_PREFIX - not shared via import, since that file
// runs in a separate worker global scope with its own script (same reason the message
// type strings above are duplicated instead of imported). Matched by prefix rather than
// the exact SHELL_CACHE/RUNTIME_CACHE names (which also embed CACHE_VERSION) so the
// Cache Storage fallback below doesn't need updating every time that version bumps.
const CACHE_PREFIX = 'gameplan-readonly-offline'
// ASSET_CACHE (gameplan-sw.js) is content-addressed /assets build output, identical for
// every user - the one bucket clearUserCaches() there deliberately leaves alone. The
// fallback below must leave it alone too.
const ASSET_CACHE_SUFFIX = ':assets'

export function setupOfflineSupport() {
  // Runs even in dev / non-secure contexts (unlike SW registration below): this is what
  // makes the dev user switcher (DevUserSwitcher.vue) safe to test with, and it's cheap
  // enough to always run at boot. Fire-and-forget here specifically - nothing after this
  // call in the boot sequence depends on the switch being fully resolved, unlike
  // session.ts's login handler, which awaits guardAgainstUserSwitch directly because it
  // hard-navigates right after.
  guardAgainstUserSwitch(getSessionUserFromCookie()).catch((error) =>
    console.error('Failed to run user-switch guard', error),
  )

  if (!serviceWorkerSupportEnabled()) {
    return
  }

  const register = () => {
    navigator.serviceWorker
      .register(SERVICE_WORKER_URL, { scope: SERVICE_WORKER_SCOPE })
      .then(async (registration) => {
        await unregisterLegacyServiceWorkers(registration)
        await warmLoadedAssets(registration)
        watchForUpdates(registration)
        onReconnect(() => registration.update().catch(() => {}))
      })
      .catch((error) => {
        console.error('Failed to register Gameplan service worker', error)
      })
  }

  if (document.readyState === 'complete') {
    register()
  } else {
    window.addEventListener('load', register, { once: true })
  }

  watchForControllerChange()
}

// Shared by setupOfflineSupport's own registration gate and clearServiceWorkerCaches'
// decision whether it's worth waiting for a registration to appear (see getActiveWorker) -
// in every case this returns false, no worker will ever be registered for this tab, so
// there's nothing to wait for.
function serviceWorkerSupportEnabled(): boolean {
  return (
    !import.meta.env.DEV &&
    typeof navigator !== 'undefined' &&
    typeof window !== 'undefined' &&
    window.isSecureContext &&
    'serviceWorker' in navigator
  )
}

export function isBrowserOffline() {
  return typeof navigator !== 'undefined' && navigator.onLine === false
}

export function isNetworkError(error: unknown) {
  return error instanceof TypeError && error.message === 'Failed to fetch'
}

/**
 * Shared-computer safety (PR #516's main review finding): wipe every trace of offline
 * content this browser holds, so the next person logged in on this machine can't read
 * a previous user's cached data. Call this on logout.
 *
 * Covers two physically separate stores:
 * - The service worker's SHELL_CACHE and RUNTIME_CACHE (app shell HTML + cached
 *   avatars/files) - the hashed /assets build cache is content-addressed and the same
 *   for every user, so the worker deliberately leaves it alone.
 * - The idb-keyval default store (IndexedDB db `keyval-store`, object store `keyval`) -
 *   frappe-ui's shared backing store for useList/useCall's persisted cache, useDoc's
 *   docStore, and the legacy Options-API listResource's saveLocal/getLocal. None of
 *   these call idb-keyval's `createStore` with a custom store, so clearing this one
 *   store wipes all of them at once (verified by reading frappe-ui beta.28's
 *   idbStore.ts, docStore.ts, resources/local.ts and resources/listResource.js).
 *
 * Deliberately does NOT touch `gameplan-drafts` (draftStore.ts's own custom idb-keyval
 * store): a plain logout+re-login as the *same* user on the same device should still be
 * able to recover an in-progress draft, and useDraftSync already guards reads by
 * `record.user` so leaving another account's draft rows on disk isn't a leak. Drafts are
 * only wiped when a genuine user switch is detected - see guardAgainstUserSwitch below,
 * which calls clearDraftStore itself alongside this function.
 *
 * Resolves to whether every store actually confirmed it was cleared - see
 * guardAgainstUserSwitch, which only records the switch as handled when this is true.
 */
export async function clearOfflineCaches(): Promise<boolean> {
  const [cachesCleared, idbCleared] = await Promise.all([
    clearServiceWorkerCaches(),
    clearIdbKeyval()
      .then(() => true)
      .catch((error) => {
        console.error('Failed to clear IndexedDB cache', error)
        return false
      }),
  ])
  return cachesCleared && idbCleared
}

/**
 * Review finding (PR #571): this used to resolve on ANY message from the worker,
 * discarding the `{ ok: true | false }` payload gameplan-sw.js's CLEAR_USER_CACHES
 * handler actually sends - a reported failure (or the 2s timeout below) was silently
 * treated the same as success. Now resolves to the worker's real answer, and falls back
 * to deleting the same caches directly when it doesn't confirm one - not registered yet,
 * unsupported, timed out, or an explicit `{ ok: false }`. Cache Storage is available
 * from the page itself, not just inside the worker, so this fallback doesn't need the
 * worker's cooperation at all.
 *
 * Follow-up review finding: `requestWorkerClear` can *reject*, not just resolve false -
 * `postMessage` throws synchronously (auto-rejecting the wrapping Promise) if the worker
 * became redundant between the registration lookup and the send, and the lookup itself
 * can reject too. Left uncaught, that used to skip the direct fallback below entirely
 * and propagate out of `clearOfflineCaches` - breaking session.ts's logout redirect
 * (no try/catch there) rather than just failing to clear a cache.
 */
async function clearServiceWorkerCaches(): Promise<boolean> {
  const confirmed = await requestWorkerClear().catch((error) => {
    console.error('Failed to reach the service worker to clear caches', error)
    return false
  })
  if (confirmed) return true
  return clearCachesDirectly()
}

function requestWorkerClear(): Promise<boolean> {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
    return Promise.resolve(false)
  }

  return getActiveWorker().then((activeWorker) => {
    if (!activeWorker) return false

    return new Promise<boolean>((resolve) => {
      const channel = new MessageChannel()
      // Don't let logout hang forever if a stuck/buggy worker never responds - the
      // Cache Storage fallback in clearServiceWorkerCaches covers this either way.
      const timeoutId = window.setTimeout(() => resolve(false), 2000)
      channel.port1.onmessage = (event) => {
        window.clearTimeout(timeoutId)
        resolve(event.data?.ok === true)
      }
      activeWorker.postMessage({ type: CLEAR_USER_CACHES_MESSAGE }, [channel.port2])
    })
  })
}

async function clearCachesDirectly(): Promise<boolean> {
  if (typeof caches === 'undefined') return true // Nothing this context could have cached.

  try {
    const names = await caches.keys()
    const userCacheNames = names.filter(
      (name) => name.startsWith(`${CACHE_PREFIX}:`) && !name.endsWith(ASSET_CACHE_SUFFIX),
    )
    const results = await Promise.all(userCacheNames.map((name) => caches.delete(name)))
    return results.every(Boolean)
  } catch (error) {
    console.error('Failed to clear caches directly', error)
    return false
  }
}

const REGISTRATION_WAIT_TIMEOUT_MS = 3000

/**
 * Round-4 follow-up finding: `guardAgainstUserSwitch` runs synchronously at the very top
 * of `setupOfflineSupport`, before that function's own `navigator.serviceWorker.register()`
 * call. On a switch detected at boot, a plain `getRegistration()` can come back with no
 * active worker even though a worker registered by an *earlier* browser session for this
 * origin is still sitting there holding the previous user's SHELL_CACHE - the clear would
 * silently no-op and report success. Only fall back to waiting when a worker is actually
 * going to show up (serviceWorkerSupportEnabled) and bound the wait, so a browser/build
 * that will never register one (dev, insecure context) doesn't hang the clear.
 */
async function getActiveWorker(): Promise<ServiceWorker | undefined> {
  const registration = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_SCOPE)
  if (registration?.active) return registration.active
  if (!serviceWorkerSupportEnabled()) return undefined

  const ready = await Promise.race([
    navigator.serviceWorker.ready,
    new Promise<undefined>((resolve) =>
      window.setTimeout(() => resolve(undefined), REGISTRATION_WAIT_TIMEOUT_MS),
    ),
  ])
  return ready?.active
}

/**
 * Round-4 finding: without this, the SW's SHELL_CACHE stays empty from the moment a
 * user-switch clear runs (clearOfflineCaches, above) until the *next* successful online
 * navigation to /g - if the browser goes offline before that happens, even a reload of
 * the page already open fails with net::ERR_FAILED instead of falling back to the
 * offline UI. Fired only after guardAgainstUserSwitch's clear resolves, a moment known
 * to be online (a user just logged in). Deliberately not run after a plain logout
 * (clearOfflineCaches's other call site, data/session.ts) - an empty shell cache is the
 * intended post-logout state there, same as every other offline cache.
 */
async function rewarmShellCache(): Promise<void> {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return

  const registration = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_SCOPE)
  registration?.active?.postMessage({ type: WARM_SHELL_CACHE_MESSAGE })
}

/**
 * Compares `user` against the last user this browser saw (persisted in localStorage so
 * it survives full reloads) and clears every offline cache when they differ. Resolves to
 * whether a switch was detected.
 *
 * Every cacheKey in the data layer (data/communities.ts, data/users.ts, data/drafts.ts)
 * is computed once from the session cookie at module-eval time - correct for a fresh
 * page load (the cookie is already the new user's by the time this module runs), but
 * stale for a user switch that happens *without* a reload. Callers that change the
 * session user in place (e.g. session.ts's login) must force a reload after a detected
 * switch instead of relying on those singletons to pick up the new identity.
 *
 * Round-4 finding (PR #516): the clear used to be started and left to run in the
 * background while this function returned synchronously. session.ts's login handler
 * hard-navigates the instant it sees `true` back from here, which could tear the page
 * down mid-clear - and the marker below was written unconditionally, so a switch that
 * got cut off still looked "handled" on the next boot. This is now async: callers that
 * are about to navigate away (session.ts) must `await` it.
 *
 * Review finding (PR #571): the marker used to be written once the clear settled
 * "successfully or not," which papered over `clearServiceWorkerCaches` silently
 * discarding the worker's own failure signal - the marker was written even when the
 * clear had genuinely failed, so a later boot never retried it. The marker is now
 * written only once `clearOfflineCaches` confirms every store actually cleared; on
 * failure this returns without touching it, so the same mismatch is seen (and the
 * clear retried) the next time this runs.
 */
export async function guardAgainstUserSwitch(user: string | null): Promise<boolean> {
  if (typeof localStorage === 'undefined') return false

  const lastSeenUser = localStorage.getItem(LAST_SEEN_USER_STORAGE_KEY)
  const switched = Boolean(lastSeenUser && user && lastSeenUser !== user)
  if (switched) {
    let cleared = false
    try {
      // Unlike a plain logout (clearOfflineCaches alone), a detected switch to a
      // *different* user also wipes gameplan-drafts - the same-user recovery case that
      // policy exists for doesn't apply here.
      const [offlineCachesCleared] = await Promise.all([clearOfflineCaches(), clearDraftStore()])
      cleared = offlineCachesCleared
    } catch (error) {
      console.error('Failed to clear offline caches', error)
    }

    if (!cleared) {
      return switched
    }

    await rewarmShellCache()
  }

  if (user) {
    localStorage.setItem(LAST_SEEN_USER_STORAGE_KEY, user)
  } else {
    localStorage.removeItem(LAST_SEEN_USER_STORAGE_KEY)
  }

  return switched
}

// A local copy, not an import from data/session.ts: session.ts imports this module (to
// call clearOfflineCaches/guardAgainstUserSwitch on login/logout), so importing `session`
// back here would cycle. Same cookie-read pattern data/communities.ts, data/users.ts and
// data/session.ts itself use, each for their own version of this trap.
function getSessionUserFromCookie(): string | null {
  const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  const user = cookies.get('user_id')
  return user && user !== 'Guest' ? user : null
}

/**
 * Surfaces a "new version available" toast once an updated worker has finished
 * installing behind the currently active one (it never auto-activates - see
 * gameplan-sw.js's install handler). Also checks for a worker that was already sitting
 * in `waiting` before this listener attached (e.g. this tab was open across the deploy).
 */
function watchForUpdates(registration: ServiceWorkerRegistration) {
  if (registration.waiting && navigator.serviceWorker.controller) {
    notifyUpdateAvailable(registration.waiting)
  }

  registration.addEventListener('updatefound', () => {
    const installingWorker = registration.installing
    if (!installingWorker) return

    installingWorker.addEventListener('statechange', () => {
      if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
        notifyUpdateAvailable(installingWorker)
      }
    })
  })
}

function notifyUpdateAvailable(worker: ServiceWorker) {
  toast('A new version of Gameplan is available', {
    duration: Infinity,
    action: {
      label: 'Refresh',
      onClick: () => worker.postMessage({ type: SKIP_WAITING_MESSAGE }),
    },
  })
}

/** Reloads once the newly-activated worker takes control, so the refresh action above
 *  actually picks up the new code. Guarded by a once-flag: `controllerchange` can also
 *  fire for reasons unrelated to our SKIP_WAITING message, and reloading more than once
 *  would loop. */
function watchForControllerChange() {
  let reloaded = false
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloaded) return
    reloaded = true
    window.location.reload()
  })
}

async function unregisterLegacyServiceWorkers(currentRegistration: ServiceWorkerRegistration) {
  const registrations = await navigator.serviceWorker.getRegistrations()
  const legacyScope = new URL('/g/', window.location.origin).href

  await Promise.all(
    registrations
      .filter((registration) => {
        return (
          registration.scope === legacyScope && registration.scope !== currentRegistration.scope
        )
      })
      .map((registration) => registration.unregister()),
  )
}

async function warmLoadedAssets(registration: ServiceWorkerRegistration) {
  await navigator.serviceWorker.ready
  postLoadedAssetsToWorker(registration)
  window.setTimeout(() => postLoadedAssetsToWorker(registration), 3000)
}

function postLoadedAssetsToWorker(registration: ServiceWorkerRegistration) {
  const urls = getLoadedAssetUrls()
  if (!urls.length) return

  registration.active?.postMessage({
    type: CACHE_URLS_MESSAGE,
    urls,
  })
}

function getLoadedAssetUrls() {
  return performance
    .getEntriesByType('resource')
    .map((entry) => entry.name)
    .filter(isSameOriginAssetUrl)
}

function isSameOriginAssetUrl(url: string) {
  try {
    const assetUrl = new URL(url)
    return assetUrl.origin === window.location.origin && assetUrl.pathname.startsWith('/assets/')
  } catch {
    return false
  }
}
