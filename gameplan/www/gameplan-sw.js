const CACHE_PREFIX = "gameplan-readonly-offline";
const CACHE_VERSION = "v8";
const SHELL_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:shell`;
const ASSET_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:assets`;
// Images are per user and cleared on logout; build files (ASSET_CACHE) are shared and kept.
// Unversioned, so a new worker keeps what was downloaded.
const RUNTIME_CACHE = `${CACHE_PREFIX}:runtime`;
const DOWNLOAD_CACHE = `${CACHE_PREFIX}:downloads`;
const APP_SHELL_URL = "/g";
const OFFLINE_ASSET_MANIFEST_URL =
  "/assets/gameplan/frontend/gameplan-offline-assets.json";
const PRECACHE_URLS = [
  APP_SHELL_URL,
  "/assets/gameplan/manifest/site.webmanifest",
  "/assets/gameplan/manifest/manifest-icon-192.maskable.png",
  "/assets/gameplan/manifest/manifest-icon-512.maskable.png",
];
const CACHEABLE_DESTINATIONS = new Set(["font", "image", "script", "style"]);
// Images seen while browsing; downloads keep theirs in DOWNLOAD_CACHE.
const MAX_BROWSED_IMAGES = 300;
const FETCHES_AT_ONCE = 4;

self.addEventListener("install", (event) => {
  event.waitUntil(warmShellCache());
  // No skipWaiting(): a new version waits until the page's update toast confirms it.
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
    event.respondWith(networkFirstNavigation(event));
    return;
  }

  if (isApiRequest(url)) return;

  if (url.pathname.startsWith("/assets/")) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (CACHEABLE_DESTINATIONS.has(request.destination)) {
    event.respondWith(staleWhileRevalidate(event));
  }
});

self.addEventListener("message", (event) => {
  const type = event.data?.type;

  if (type === "CACHE_IMAGES" && Array.isArray(event.data.urls)) {
    event.waitUntil(cacheImages(event.data.urls));
    return;
  }

  if (type === "FORGET_IMAGES" && Array.isArray(event.data.urls)) {
    event.waitUntil(forgetImages(event.data.urls));
    return;
  }

  if (type === "SKIP_WAITING") {
    self.skipWaiting();
    return;
  }

  if (type === "WARM_SHELL_CACHE") {
    // Sent after a user-switch clear, so the app still opens offline before the next
    // navigation. After logout the shell stays empty.
    event.waitUntil(warmShellCache());
  }
});

async function warmShellCache() {
  const cache = await caches.open(SHELL_CACHE);
  await Promise.all(
    PRECACHE_URLS.map(async (url) => {
      try {
        const response = await fetch(
          new Request(url, { credentials: "include", cache: "reload" }),
        );
        if (isCacheableResponse(response)) await cache.put(url, response);
      } catch {
        // The runtime fetch handler will populate the cache once the app is online.
      }
    }),
  );
  await cacheBuild();
}

async function deleteOldCaches() {
  const currentCaches = new Set([
    SHELL_CACHE,
    ASSET_CACHE,
    RUNTIME_CACHE,
    DOWNLOAD_CACHE,
  ]);
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

/** The page is answered at once; the shell and the build are refreshed after. */
async function networkFirstNavigation(event) {
  try {
    const response = await fetch(event.request);
    if (isHtmlResponse(response)) {
      event.waitUntil(refreshShell(response.clone()));
    }
    return response;
  } catch {
    const cache = await caches.open(SHELL_CACHE);
    const cachedRequest = await cache.match(event.request);
    const cachedShell = await cache.match(APP_SHELL_URL);
    return cachedRequest || cachedShell || Response.error();
  }
}

async function refreshShell(response) {
  const cache = await caches.open(SHELL_CACHE);
  await cache.put(APP_SHELL_URL, response);
  await cacheBuild();
}

/**
 * Saves every file of the current build (the manifest vite.config.ts writes), so a route
 * never opened online still loads offline, and drops the files of older builds.
 */
async function cacheBuild() {
  try {
    const response = await fetch(OFFLINE_ASSET_MANIFEST_URL, { cache: "no-cache" });
    if (!isCacheableResponse(response)) return;
    const urls = await response.json();
    if (!Array.isArray(urls) || !urls.length) return;
    const cache = await caches.open(ASSET_CACHE);
    await saveAll(cache, urls.filter(isAssetUrl));
    await deleteOldBuildAssets(cache, urls);
  } catch {
    // Offline, or an older build without the manifest: assets are cached as they load.
  }
}

/** Saves `url` into `cache` unless it is already there; a failure waits for the next try. */
async function save(cache, url) {
  const request = new Request(url, { credentials: "include" });
  try {
    if (await cache.match(request)) return;
    const response = await fetch(request);
    if (isCacheableResponse(response)) await cache.put(request, response);
  } catch {
    // Offline, or the server refused it: the next visit or sync tries again.
  }
}

/** A few at a time, so a first visit or download doesn't request everything at once. */
async function saveAll(cache, urls) {
  const queue = [...urls];
  const next = async () => {
    while (queue.length) await save(cache, queue.shift());
  };
  await Promise.all(Array.from({ length: FETCHES_AT_ONCE }, next));
}

// Offline downloads (offlineDownloads.ts): images inside downloaded discussions and custom
// emojis.
async function cacheImages(urls) {
  const cache = await caches.open(DOWNLOAD_CACHE);
  await saveAll(cache, urls.filter(isUploadedFileUrl));
  // The settings show what the downloads weigh, and these are part of it.
  for (const client of await self.clients.matchAll()) {
    client.postMessage({ type: "IMAGES_SAVED" });
  }
}

async function forgetImages(urls) {
  const cache = await caches.open(DOWNLOAD_CACHE);
  await Promise.all(
    urls.filter(isUploadedFileUrl).map((url) => cache.delete(url)),
  );
}

/** Whether `url` is on this origin, under one of `prefixes`. */
function onOrigin(url, ...prefixes) {
  try {
    const { origin, pathname } = new URL(url, self.location.origin);
    return (
      origin === self.location.origin &&
      prefixes.some((prefix) => pathname.startsWith(prefix))
    );
  } catch {
    return false;
  }
}

const isAssetUrl = (url) => onOrigin(url, "/assets/");
const isUploadedFileUrl = (url) => onOrigin(url, "/files/", "/private/files/");

// Build files are content-hashed, so every deploy adds a new set (~5 MB) under the same
// ASSET_CACHE. Keep only the current build's; the server no longer has the old ones anyway.
const BUILD_ASSETS_PATH = "/assets/gameplan/frontend/assets/";

async function deleteOldBuildAssets(cache, currentUrls) {
  const current = new Set(
    currentUrls.map((url) => new URL(url, self.location.origin).pathname),
  );
  const requests = await cache.keys();
  await Promise.all(
    requests
      .filter((request) => {
        const { pathname } = new URL(request.url);
        return pathname.startsWith(BUILD_ASSETS_PATH) && !current.has(pathname);
      })
      .map((request) => cache.delete(request)),
  );
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

// Uploaded images rarely change, so a saved copy is refreshed at most once a day, and never
// while offline, where the request can only fail.
const IMAGE_REFRESH_AFTER = 24 * 60 * 60 * 1000;

async function staleWhileRevalidate(event) {
  const request = event.request;
  // A downloaded copy counts too: caches.match looks in every cache.
  const cached = await caches.match(request);
  if (!self.navigator.onLine) return cached || Response.error();
  if (cached && isRecent(cached)) return cached;

  const fetched = fetch(request)
    .then((response) => {
      if (isCacheableResponse(response)) {
        event.waitUntil(saveBrowsed(request, response.clone()));
      }
      return response;
    })
    .catch(() => null);

  return cached || (await fetched) || Response.error();
}

/** Keeps the newest MAX_BROWSED_IMAGES, oldest out first. */
async function saveBrowsed(request, response) {
  const cache = await caches.open(RUNTIME_CACHE);
  await cache.put(request, response);
  const keys = await cache.keys();
  await Promise.all(
    keys
      .slice(0, Math.max(0, keys.length - MAX_BROWSED_IMAGES))
      .map((key) => cache.delete(key)),
  );
}

function isRecent(response) {
  const fetchedAt = Date.parse(response.headers.get("date"));
  return Date.now() - fetchedAt < IMAGE_REFRESH_AFTER;
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
