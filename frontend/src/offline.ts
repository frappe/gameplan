const SERVICE_WORKER_URL = '/gameplan-sw.js'
const SERVICE_WORKER_SCOPE = '/g'
const CACHE_URLS_MESSAGE = 'CACHE_URLS'

export function setupOfflineSupport() {
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
}

export function isBrowserOffline() {
  return typeof navigator !== 'undefined' && navigator.onLine === false
}

export function isNetworkError(error: unknown) {
  return error instanceof TypeError && error.message === 'Failed to fetch'
}

async function unregisterLegacyServiceWorkers(currentRegistration: ServiceWorkerRegistration) {
  const registrations = await navigator.serviceWorker.getRegistrations()
  const legacyScope = new URL('/g/', window.location.origin).href

  await Promise.all(
    registrations
      .filter((registration) => {
        return registration.scope === legacyScope && registration.scope !== currentRegistration.scope
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
