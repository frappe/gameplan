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

export function setupOfflineSupport() {
  // Runs even in dev / non-secure contexts (unlike SW registration below): this is what
  // makes the dev user switcher (DevUserSwitcher.vue) safe to test with, and it's cheap
  // enough to always run at boot.
  guardAgainstUserSwitch(getSessionUserFromCookie())

  if (
    import.meta.env.DEV ||
    typeof navigator === 'undefined' ||
    !window.isSecureContext ||
    !('serviceWorker' in navigator)
  ) {
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
 */
export async function clearOfflineCaches(): Promise<void> {
  await Promise.all([
    clearServiceWorkerCaches(),
    clearIdbKeyval().catch((error) => console.error('Failed to clear IndexedDB cache', error)),
  ])
}

async function clearServiceWorkerCaches(): Promise<void> {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return

  const registration = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_SCOPE)
  const activeWorker = registration?.active
  if (!activeWorker) return

  await new Promise<void>((resolve) => {
    const channel = new MessageChannel()
    // Don't let logout hang forever if a stuck/buggy worker never responds.
    const timeoutId = window.setTimeout(resolve, 2000)
    channel.port1.onmessage = () => {
      window.clearTimeout(timeoutId)
      resolve()
    }
    activeWorker.postMessage({ type: CLEAR_USER_CACHES_MESSAGE }, [channel.port2])
  })
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
 * it survives full reloads) and clears every offline cache when they differ. Returns
 * whether a switch was detected.
 *
 * Every cacheKey in the data layer (data/communities.ts, data/users.ts, data/drafts.ts)
 * is computed once from the session cookie at module-eval time - correct for a fresh
 * page load (the cookie is already the new user's by the time this module runs), but
 * stale for a user switch that happens *without* a reload. Callers that change the
 * session user in place (e.g. session.ts's login) must force a reload after a detected
 * switch instead of relying on those singletons to pick up the new identity.
 */
export function guardAgainstUserSwitch(user: string | null): boolean {
  if (typeof localStorage === 'undefined') return false

  const lastSeenUser = localStorage.getItem(LAST_SEEN_USER_STORAGE_KEY)
  const switched = Boolean(lastSeenUser && user && lastSeenUser !== user)
  if (switched) {
    // Unlike a plain logout (clearOfflineCaches alone), a detected switch to a
    // *different* user also wipes gameplan-drafts - the same-user recovery case that
    // policy exists for doesn't apply here.
    Promise.all([clearOfflineCaches(), clearDraftStore()])
      .then(() => rewarmShellCache())
      .catch((error) => console.error('Failed to clear offline caches', error))
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
