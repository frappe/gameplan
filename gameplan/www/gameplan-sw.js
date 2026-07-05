const CACHE_PREFIX = "gameplan-readonly-offline";
const CACHE_VERSION = "v5";
const SHELL_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:shell`;
const ASSET_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:assets`;
const APP_SHELL_URL = "/g";
const OFFLINE_ASSET_MANIFEST_URL =
  "/assets/gameplan/frontend/gameplan-offline-assets.json";
const PRECACHE_URLS = [
  APP_SHELL_URL,
  OFFLINE_ASSET_MANIFEST_URL,
  "/assets/gameplan/manifest/site.webmanifest",
  "/assets/gameplan/manifest/manifest-icon-192.maskable.png",
  "/assets/gameplan/manifest/manifest-icon-512.maskable.png",
];
const CACHEABLE_DESTINATIONS = new Set(["font", "image", "script", "style"]);

self.addEventListener("install", (event) => {
  event.waitUntil(warmShellCache());
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(deleteOldCaches());
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (isGameplanNavigation(request, url)) {
    event.respondWith(networkFirstNavigation(request));
    return;
  }

  if (isApiRequest(url)) return;

  if (url.pathname.startsWith("/assets/")) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (CACHEABLE_DESTINATIONS.has(request.destination)) {
    event.respondWith(staleWhileRevalidate(request));
  }
});

self.addEventListener("message", (event) => {
  if (event.data?.type !== "CACHE_URLS" || !Array.isArray(event.data.urls))
    return;
  event.waitUntil(cacheUrls(event.data.urls));
});

async function warmShellCache() {
  const cache = await caches.open(SHELL_CACHE);
  await Promise.all(
    PRECACHE_URLS.map(async (url) => {
      try {
        const response = await fetch(
          new Request(url, { credentials: "include", cache: "reload" }),
        );
        if (isCacheableResponse(response)) {
          await cache.put(url, response.clone());
          if (isHtmlResponse(response)) {
            await cacheShellAssets(response);
          }
          if (url === OFFLINE_ASSET_MANIFEST_URL) {
            await cacheOfflineAssetManifest(response.clone());
          }
        }
      } catch {
        // The runtime fetch handler will populate the cache once the app is online.
      }
    }),
  );
}

async function deleteOldCaches() {
  const currentCaches = new Set([SHELL_CACHE, ASSET_CACHE]);
  const names = await caches.keys();
  await Promise.all(
    names
      .filter(
        (name) => name.startsWith(CACHE_PREFIX) && !currentCaches.has(name),
      )
      .map((name) => caches.delete(name)),
  );
}

function isGameplanNavigation(request, url) {
  return (
    request.mode === "navigate" &&
    (url.pathname === "/g" || url.pathname.startsWith("/g/"))
  );
}

function isApiRequest(url) {
  return (
    url.pathname.startsWith("/api/") || url.pathname.startsWith("/socket.io/")
  );
}

async function networkFirstNavigation(request) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const response = await fetch(request);
    if (isHtmlResponse(response)) {
      await cache.put(APP_SHELL_URL, response.clone());
      await cacheShellAssets(response.clone());
    }
    return response;
  } catch {
    const cachedRequest = await cache.match(request);
    const cachedShell = await cache.match(APP_SHELL_URL);
    return cachedRequest || cachedShell || Response.error();
  }
}

async function cacheShellAssets(response) {
  const urls = getShellAssetUrls(await response.text());
  await cacheUrls(urls);
  await cacheOfflineAssetManifest();
}

function getShellAssetUrls(html) {
  const urls = new Set();
  const assetPattern = /\b(?:src|href)=["']([^"']+)["']/g;

  for (const match of html.matchAll(assetPattern)) {
    const url = new URL(match[1], self.location.origin);
    if (
      url.origin === self.location.origin &&
      url.pathname.startsWith("/assets/")
    ) {
      urls.add(url.href);
    }
  }

  return [...urls];
}

async function cacheUrls(urls) {
  const cache = await caches.open(ASSET_CACHE);
  const sameOriginAssetUrls = urls.filter(isSameOriginAssetUrl);

  await Promise.all(
    sameOriginAssetUrls.map(async (url) => {
      try {
        const request = new Request(url, { credentials: "include" });
        const cached = await cache.match(request);
        if (cached) return;

        const response = await fetch(request);
        if (isCacheableResponse(response)) {
          await cache.put(request, response);
        }
      } catch {
        // The next online visit to the route will retry this asset.
      }
    }),
  );
}

async function cacheOfflineAssetManifest(response) {
  try {
    const manifestResponse =
      response ||
      (await fetch(OFFLINE_ASSET_MANIFEST_URL, { cache: "reload" }));
    if (!isCacheableResponse(manifestResponse)) return;

    const urls = await manifestResponse.clone().json();
    if (Array.isArray(urls)) {
      await cacheUrls(urls);
    }
  } catch {
    // Older builds do not have the manifest; route assets will still be cached as they load.
  }
}

function isSameOriginAssetUrl(url) {
  try {
    const assetUrl = new URL(url, self.location.origin);
    return (
      assetUrl.origin === self.location.origin &&
      assetUrl.pathname.startsWith("/assets/")
    );
  } catch {
    return false;
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(ASSET_CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (isCacheableResponse(response)) {
      await cache.put(request, response.clone());
    }
    return response;
  } catch {
    return Response.error();
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(ASSET_CACHE);
  const cached = await cache.match(request);
  const fetched = fetch(request)
    .then((response) => {
      if (isCacheableResponse(response)) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);

  return cached || (await fetched) || Response.error();
}

function isCacheableResponse(response) {
  return response && response.ok && response.type === "basic";
}

function isHtmlResponse(response) {
  return (
    isCacheableResponse(response) &&
    response.headers.get("content-type")?.includes("text/html")
  );
}
