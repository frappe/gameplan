import { clear as clearIdbKeyval } from 'idb-keyval'
import { toast } from 'frappe-ui'
import { clearDraftStore } from '@/data/draftStore'
import { onReconnect } from '@/data/online'
import { getSessionUserFromCookie } from '@/utils/sessionCookie'

const SERVICE_WORKER_URL = '/gameplan-sw.js'
const SERVICE_WORKER_SCOPE = '/g'
const CACHE_URLS_MESSAGE = 'CACHE_URLS'
const CLEAR_USER_CACHES_MESSAGE = 'CLEAR_USER_CACHES'
const WARM_SHELL_CACHE_MESSAGE = 'WARM_SHELL_CACHE'
const SKIP_WAITING_MESSAGE = 'SKIP_WAITING'
const LAST_SEEN_USER_STORAGE_KEY = 'gameplan:last-seen-user'
// Duplicated from gameplan-sw.js, which runs as a separate script and can't be imported.
const CACHE_PREFIX = 'gameplan-readonly-offline'
// Build files are the same for every user, so clearing a user's caches leaves them.
const ASSET_CACHE_SUFFIX = ':assets'

/**
 * Whether it is safe to show the app: either nobody switched, or the previous user's data is
 * gone. The session can change outside the app's own login (a switched cookie, `bench browse
 * --sid`, the dev user switcher), and the doc cache is keyed by doctype and name alone, so a
 * read queued by a mounting component would otherwise hand the new user the old one's copy.
 *
 * Never rejects: a thrown guard counts as not cleared, which the caller must not treat as
 * safe.
 */
export async function clearCachesOnUserSwitch(): Promise<boolean> {
  const { switched, cleared } = await guardAgainstUserSwitch(getSessionUserFromCookie()).catch(
    (error) => {
      console.error('Failed to run user-switch guard', error)
      return { switched: true, cleared: false }
    },
  )
  return !switched || cleared
}

export function setupOfflineSupport() {
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

function serviceWorkerSupportEnabled(): boolean {
  return (
    !import.meta.env.DEV &&
    typeof navigator !== 'undefined' &&
    typeof window !== 'undefined' &&
    window.isSecureContext &&
    'serviceWorker' in navigator
  )
}

export function isNetworkError(error: unknown) {
  // Chrome, Safari and Firefox each word a failed fetch differently.
  return (
    error instanceof TypeError && /Failed to fetch|Load failed|NetworkError/.test(error.message)
  )
}

/**
 * Wipes what this browser holds offline, so the next person to sign in can't read it.
 * Resolves to whether every store cleared. Drafts are kept for the same user signing back
 * in; a user switch clears them too (guardAgainstUserSwitch).
 */
export async function clearOfflineCaches(): Promise<boolean> {
  const [cachesCleared, idbCleared] = await Promise.all([
    clearServiceWorkerCaches(),
    within(
      clearIdbKeyval().then(() => true),
      IDB_DELETE_TIMEOUT_MS,
      false,
    )
      .then((cleared) => (cleared ? true : deleteIdbStore()))
      .catch((error) => {
        console.error('Failed to clear IndexedDB cache', error)
        return deleteIdbStore()
      }),
  ])
  return cachesCleared && idbCleared
}

// idb-keyval's default database, dropped when emptying it fails.
const IDB_NAME = 'keyval-store'
const IDB_DELETE_TIMEOUT_MS = 2000

/** `promise`, or `fallback` if it has not settled within `ms`. */
function within<T>(promise: Promise<T>, ms: number, fallback: T): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((resolve) => window.setTimeout(() => resolve(fallback), ms)),
  ])
}

function deleteIdbStore(): Promise<boolean> {
  if (typeof indexedDB === 'undefined') return Promise.resolve(false)
  return new Promise<boolean>((resolve) => {
    let settled = false
    const timeoutId = window.setTimeout(() => done(false), IDB_DELETE_TIMEOUT_MS)
    const done = (ok: boolean) => {
      if (settled) return
      settled = true
      window.clearTimeout(timeoutId)
      resolve(ok)
    }
    try {
      const request = indexedDB.deleteDatabase(IDB_NAME)
      request.onsuccess = () => done(true)
      request.onerror = () => done(false)
      request.onblocked = () => done(false)
    } catch (error) {
      console.error('Failed to delete the IndexedDB store', error)
      done(false)
    }
  })
}

/**
 * Asks the worker to clear, and deletes the caches from the page itself whenever the worker
 * doesn't confirm it (none registered yet, a timeout, a failure, or an error reaching it).
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
      // A worker that never answers mustn't hang logout; the direct clear covers it.
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
 * At boot the worker from an earlier visit may not be active yet, so wait for it (briefly,
 * and only where one will register) rather than report a clear that never reached it.
 */
async function getActiveWorker(): Promise<ServiceWorker | undefined> {
  const registration = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_SCOPE)
  if (registration?.active) return registration.active
  if (!serviceWorkerSupportEnabled()) return undefined

  const ready = await within<ServiceWorkerRegistration | undefined>(
    navigator.serviceWorker.ready,
    REGISTRATION_WAIT_TIMEOUT_MS,
    undefined,
  )
  return ready?.active ?? undefined
}

/**
 * Refills the app shell after a user-switch clear, so a reload that goes offline before the
 * next navigation still opens the app. Not after logout, where an empty cache is the point.
 */
async function rewarmShellCache(): Promise<void> {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return

  const registration = await navigator.serviceWorker.getRegistration(SERVICE_WORKER_SCOPE)
  registration?.active?.postMessage({ type: WARM_SHELL_CACHE_MESSAGE })
}

interface UserSwitch {
  /** The signed-in user differs from the last this browser saw. */
  switched: boolean
  /** Nothing of the previous user is left here. False only when a switch could not be cleared. */
  cleared: boolean
}

/**
 * Clears every offline cache when `user` differs from the last user this browser saw. The
 * marker only moves once the clear succeeds, so a failed one is retried on the next boot.
 * Cache keys are fixed at module load, so a caller switching users must reload afterwards.
 */
export async function guardAgainstUserSwitch(user: string | null): Promise<UserSwitch> {
  try {
    if (typeof localStorage === 'undefined') return { switched: false, cleared: true }

    const lastSeenUser = localStorage.getItem(LAST_SEEN_USER_STORAGE_KEY)
    const switched = Boolean(lastSeenUser && user && lastSeenUser !== user)
    if (switched) {
      let cleared = false
      try {
        // A different user, so drafts go too.
        const [offlineCachesCleared, draftsCleared] = await Promise.all([
          clearOfflineCaches(),
          within(
            clearDraftStore().then(() => true),
            IDB_DELETE_TIMEOUT_MS,
            false,
          ).catch((error) => {
            console.error('Failed to clear draft store', error)
            return false
          }),
        ])
        cleared = offlineCachesCleared && draftsCleared
      } catch (error) {
        console.error('Failed to clear offline caches', error)
      }

      if (!cleared) return { switched, cleared }

      await rewarmShellCache()
    }

    // A signed-out boot leaves the marker, or the next sign-in would skip the clear.
    if (user) localStorage.setItem(LAST_SEEN_USER_STORAGE_KEY, user)

    return { switched, cleared: true }
  } catch (error) {
    console.error('Failed to run user-switch guard', error)
    return { switched: true, cleared: false }
  }
}

// Not imported from data/session.ts, which imports this module.

/** Offers a refresh once a new worker is installed and waiting, including one already waiting. */
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
    id: 'app-update',
    duration: Infinity,
    action: {
      label: 'Refresh',
      onClick: () => worker.postMessage({ type: SKIP_WAITING_MESSAGE }),
    },
  })
}

/** Reloads once when a new worker takes over, so Refresh loads the new code. */
function watchForControllerChange() {
  let reloaded = false
  // The first install also fires `controllerchange` when the worker claims this page
  // (`clients.claim()`), and reloading then just loads the whole app a second time.
  let hadController = Boolean(navigator.serviceWorker.controller)
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!hadController) {
      hadController = true
      return
    }
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
