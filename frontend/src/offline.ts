import { clear as clearIdbKeyval } from 'idb-keyval'
import { toast } from 'frappe-ui'
import { clearDraftStore } from '@/data/draftStore'
import { onReconnect } from '@/data/online'
import { getSessionUserFromCookie } from '@/utils/sessionCookie'

const SERVICE_WORKER_URL = '/gameplan-sw.js'
const SERVICE_WORKER_SCOPE = '/g'
const LAST_SEEN_USER_STORAGE_KEY = 'gameplan:last-seen-user'
// Duplicated from gameplan-sw.js, which runs as a separate script and can't be imported.
const CACHE_PREFIX = 'gameplan-readonly-offline'
// Build files are the same for every user, so clearing a user's caches leaves them.
const ASSET_CACHE_SUFFIX = ':assets'

/**
 * Whether it is safe to show the app: either nobody switched, or the previous user's data is
 * gone. The session can change outside the app's own login (a switched cookie, `bench browse
 * --sid`, the dev user switcher), and frappe-ui's v1 resources and the worker's image cache
 * are not kept per user.
 */
export async function clearCachesOnUserSwitch(): Promise<boolean> {
  const { switched, cleared } = await guardAgainstUserSwitch(getSessionUserFromCookie())
  return !switched || cleared
}

export function setupOfflineSupport() {
  if (!serviceWorkerSupportEnabled()) return

  const register = () =>
    navigator.serviceWorker
      .register(SERVICE_WORKER_URL, { scope: SERVICE_WORKER_SCOPE })
      .then((registration) => {
        watchForUpdates(registration)
        onReconnect(() => registration.update().catch(() => {}))
      })
      .catch((error) => console.error('Failed to register Gameplan service worker', error))

  // The app mounts after an async check, which can finish after `load` has fired.
  if (document.readyState === 'complete') register()
  else window.addEventListener('load', register, { once: true })
  watchForControllerChange()
}

function serviceWorkerSupportEnabled() {
  return !import.meta.env.DEV && window.isSecureContext && 'serviceWorker' in navigator
}

/** Held by a download while it writes to the cache, and by a clear, so the two never overlap. */
export const DOWNLOADS_LOCK = 'gameplan-offline-downloads'

const beforeClear = new Set<() => void>()

/** Runs `stop` when the caches are about to be cleared, so a download in this tab ends first. */
export function onBeforeClear(stop: () => void) {
  beforeClear.add(stop)
}

/**
 * Wipes what this browser holds offline, so the next person to sign in can't read it.
 * Resolves to whether everything cleared. Drafts are kept for the same user signing back
 * in; a user switch clears them too (guardAgainstUserSwitch).
 */
export async function clearOfflineCaches(): Promise<boolean> {
  for (const stop of beforeClear) stop()
  // Waits for any tab's download to finish writing, so nothing lands after the clear.
  const clear = async () => {
    const results = await Promise.all([
      clearUserCaches(),
      // No IndexedDB means nothing was stored in it.
      clearIdbKeyval().then(
        () => true,
        () => typeof indexedDB === 'undefined',
      ),
    ])
    return results.every(Boolean)
  }
  return navigator.locks ? navigator.locks.request(DOWNLOADS_LOCK, clear) : clear()
}

async function clearUserCaches() {
  if (typeof caches === 'undefined') return true
  try {
    const names = (await caches.keys()).filter(
      (name) => name.startsWith(`${CACHE_PREFIX}:`) && !name.endsWith(ASSET_CACHE_SUFFIX),
    )
    return (await Promise.all(names.map((name) => caches.delete(name)))).every(Boolean)
  } catch (error) {
    console.error('Failed to clear offline caches', error)
    return false
  }
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
 * Resources already in memory belong to the previous user, so a caller switching users must
 * reload afterwards.
 */
export async function guardAgainstUserSwitch(user: string | null): Promise<UserSwitch> {
  const lastSeenUser = lastSeen.get()
  const switched = Boolean(lastSeenUser && user && lastSeenUser !== user)
  if (switched) {
    // A different user, so drafts go too.
    const [cachesCleared, draftsCleared] = await Promise.all([
      clearOfflineCaches(),
      clearDraftStore().then(
        () => true,
        () => false,
      ),
    ])
    if (!cachesCleared || !draftsCleared) return { switched, cleared: false }
    // Refills the app shell, so a reload that goes offline before the next navigation still
    // opens the app. Not after logout, where an empty cache is the point.
    navigator.serviceWorker?.controller?.postMessage({ type: 'WARM_SHELL_CACHE' })
  }
  // A signed-out boot leaves the marker, or the next sign-in would skip the clear.
  if (user) lastSeen.set(user)
  return { switched, cleared: true }
}

// With storage blocked there is no marker, so no switch to detect.
const lastSeen = {
  get() {
    try {
      return localStorage.getItem(LAST_SEEN_USER_STORAGE_KEY)
    } catch {
      return null
    }
  },
  set(user: string) {
    try {
      localStorage.setItem(LAST_SEEN_USER_STORAGE_KEY, user)
    } catch {
      // Nothing to remember it in.
    }
  },
}

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
      onClick: () => worker.postMessage({ type: 'SKIP_WAITING' }),
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
