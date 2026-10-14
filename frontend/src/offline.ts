import { clear as clearIdbKeyval } from 'idb-keyval'
import { toast } from 'frappe-ui'
import { useLocalStorage } from '@vueuse/core'
import { clearDraftStore } from '@/data/draftStore'
import { onReconnect } from '@/data/online'
import { getSessionUserFromCookie } from '@/utils/sessionCookie'
import { withLock } from '@/utils/locks'

const SERVICE_WORKER_URL = '/gameplan-sw.js'
const SERVICE_WORKER_SCOPE = '/g'

const LAST_SEEN_USER_STORAGE_KEY = 'gameplan:last-seen-user'
// Duplicated from gameplan-sw.js, which runs as a separate script and can't be imported.
const CACHE_PREFIX = 'gameplan-readonly-offline'
// Build files are the same for every user, so clearing a user's caches leaves them.
const ASSET_CACHE_SUFFIX = ':assets'
// Shared with the worker's offline-user-caches.js. Keep this marker outside user caches.
const CACHE_STATE_NAME = `${CACHE_PREFIX}-state`
const CACHE_GENERATION_KEY = '/__gameplan-offline-generation'
const USER_CACHE_LOCK = `${CACHE_PREFIX}-user-caches`

/** Whether the app may show: nobody switched, or the previous user's data is gone. The session
 *  can change outside the app's login (another tab, `bench browse --sid`, the dev switcher). */
export async function clearCachesOnUserSwitch(): Promise<boolean> {
  const { switched, cleared } = await guardAgainstUserSwitch(getSessionUserFromCookie())
  return !switched || cleared
}

export function setupOfflineSupport() {
  if (!serviceWorkerSupportEnabled()) return

  const register = () =>
    registerWorker()
      .then((registration) => {
        watchForUpdates(registration)
        onReconnect(() => registration.update().catch(() => {}))
      })
      .catch((error) => console.error('Failed to register Gameplan service worker', error))

  // The app mounts after an async check, which can finish after `load` has fired.
  if (document.readyState === 'complete') register()
  else window.addEventListener('load', register, { once: true })
  watchForControllerChange()
  window.addEventListener('pagehide', () => {
    navigator.serviceWorker?.controller?.postMessage({ type: 'CLEAN_UNUSED_BUILDS' })
  })
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

/** Wipes what this browser holds offline; resolves to whether everything cleared. Drafts stay
 *  for the same user signing back in; a user switch clears them too. */
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
  return withLock(DOWNLOADS_LOCK, clear)
}

async function clearUserCaches(): Promise<boolean> {
  if (typeof caches === 'undefined') return true
  try {
    const clear = async () => {
      const state = await caches.open(CACHE_STATE_NAME)
      await state.put(CACHE_GENERATION_KEY, new Response(crypto.randomUUID()))
      const names = (await caches.keys()).filter(
        (name) => name.startsWith(`${CACHE_PREFIX}:`) && !name.endsWith(ASSET_CACHE_SUFFIX),
      )
      const results = await Promise.all(names.map((name) => caches.delete(name)))
      navigator.serviceWorker?.controller?.postMessage({ type: 'CLEAR_USER_CACHES' })
      return results.every(Boolean)
    }
    return withLock(USER_CACHE_LOCK, clear)
  } catch (error) {
    console.error('Failed to clear offline caches', error)
    return false
  }
}

/** Bind a batch of image operations to the generation that existed before its requests. */
export async function getWorkerCacheGeneration(): Promise<string | null> {
  const worker = navigator.serviceWorker?.controller
  if (worker) {
    const answer = await new Promise((resolve) => {
      const channel = new MessageChannel()
      const timer = setTimeout(() => resolve(null), 3000)
      channel.port1.onmessage = (e) => {
        clearTimeout(timer)
        resolve(e.data)
      }
      worker.postMessage({ type: 'CACHE_GENERATION' }, [channel.port2])
    })
    if (typeof answer === 'string') return answer
  }
  return readGenerationDirect()
}

async function readGenerationDirect(): Promise<string | null> {
  try {
    const state = await caches?.open(CACHE_STATE_NAME)
    const stored = await state?.match(CACHE_GENERATION_KEY)
    if (stored) return stored.text()
    const generation = crypto.randomUUID()
    await state?.put(CACHE_GENERATION_KEY, new Response(generation))
    return generation
  } catch {
    return null
  }
}

interface UserSwitch {
  /** The signed-in user differs from the last this browser saw. */
  switched: boolean
  /** Nothing of the previous user is left here. False only when a switch could not be cleared. */
  cleared: boolean
}

/** Clears every offline cache when `user` is not the last user seen. The marker moves only
 *  after a clear succeeds, so a failed one retries on the next boot. A caller switching users
 *  must reload: what is in memory is still the previous user's. */
export async function guardAgainstUserSwitch(user: string | null): Promise<UserSwitch> {
  const lastSeenUser = lastSeen.value
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
  if (user) lastSeen.value = user
  return { switched, cleared: true }
}

// With storage blocked there is no marker, so no switch to detect.
const lastSeen = useLocalStorage<string | null>(LAST_SEEN_USER_STORAGE_KEY, null, {
  onError: () => {},
})

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

function registerWorker() {
  return navigator.serviceWorker.register(SERVICE_WORKER_URL, {
    scope: SERVICE_WORKER_SCOPE,
    updateViaCache: 'none',
  })
}
