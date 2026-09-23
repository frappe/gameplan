const CACHE_PREFIX = "gameplan-readonly-offline";
const CACHE_VERSION = "v7";
const SHELL_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:shell`;
const ASSET_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:assets`;
// Images are per user and cleared on logout; build files (ASSET_CACHE) are shared and kept.
const RUNTIME_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:runtime`;
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
  const type = event.data?.type;

  if (type === "CACHE_URLS" && Array.isArray(event.data.urls)) {
    event.waitUntil(cacheUrls(event.data.urls));
    return;
  }

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

  if (type === "CLEAR_USER_CACHES") {
    const port = event.ports[0];
    event.waitUntil(
      clearUserCaches()
        .then(() => port?.postMessage({ ok: true }))
        .catch(() => port?.postMessage({ ok: false })),
    );
    return;
  }

  if (type === "WARM_SHELL_CACHE") {
    // Sent after a user-switch clear, so the app still opens offline before the next
    // navigation. Separate from CLEAR_USER_CACHES: after logout the shell stays empty.
    event.waitUntil(warmShellCache());
  }
});

// Logout and user switch (offline.ts): drop everything holding the user's content.
async function clearUserCaches() {
  await Promise.all([caches.delete(SHELL_CACHE), caches.delete(RUNTIME_CACHE)]);
}

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
  const currentCaches = new Set([SHELL_CACHE, ASSET_CACHE, RUNTIME_CACHE]);
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
  const [assets, shell] = await Promise.all([
    caches.open(ASSET_CACHE),
    caches.open(SHELL_CACHE),
  ]);
  // The page's own build files are renamed by every build, so all of them being cached means
  // this build was seen before and its manifest already fetched. Fetching it again on every
  // page load was a request develop never made.
  const cached = await Promise.all(urls.map((url) => assets.match(url)));
  const newBuild =
    cached.some((hit) => !hit) ||
    !(await shell.match(OFFLINE_ASSET_MANIFEST_URL));
  await cacheUrls(urls);
  if (newBuild) await cacheOfflineAssetManifest();
}

function getShellAssetUrls(html) {
  const urls = new Set();
  const assetPattern = /\b(?:src|href)=["']([^"']+)["']/g;

  for (const [, href] of html.matchAll(assetPattern)) {
    if (isAssetUrl(href)) urls.add(new URL(href, self.location.origin).href);
  }

  return [...urls];
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

async function cacheUrls(urls) {
  const cache = await caches.open(ASSET_CACHE);
  await Promise.all(urls.filter(isAssetUrl).map((url) => save(cache, url)));
}

// Offline downloads (offlineDownloads.ts): images inside downloaded discussions and custom
// emojis. Kept in the runtime cache with images seen while browsing, so logout clears them.
const IMAGE_FETCHES_AT_ONCE = 4;

async function cacheImages(urls) {
  const cache = await caches.open(RUNTIME_CACHE);
  const queue = urls.filter(isUploadedFileUrl);
  // A few at a time, so a first download doesn't request every image at once.
  const next = async () => {
    while (queue.length) await save(cache, queue.shift());
  };
  await Promise.all(Array.from({ length: IMAGE_FETCHES_AT_ONCE }, next));
  // The settings show what the downloads weigh, and these are part of it.
  for (const client of await self.clients.matchAll()) {
    client.postMessage({ type: "IMAGES_SAVED" });
  }
}

async function forgetImages(urls) {
  const cache = await caches.open(RUNTIME_CACHE);
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

async function cacheOfflineAssetManifest(response) {
  try {
    const manifestResponse =
      response ||
      (await fetch(OFFLINE_ASSET_MANIFEST_URL, { cache: "reload" }));
    if (!isCacheableResponse(manifestResponse)) return;

    const urls = await manifestResponse.clone().json();
    if (Array.isArray(urls) && urls.length) {
      await cacheUrls(urls);
      await deleteOldBuildAssets(urls);
      const shell = await caches.open(SHELL_CACHE);
      await shell.put(OFFLINE_ASSET_MANIFEST_URL, manifestResponse);
    }
  } catch {
    // Older builds do not have the manifest; route assets will still be cached as they load.
  }
}

// Build files are content-hashed, so every deploy adds a new set (~5 MB) under the same
// ASSET_CACHE. Keep only the current build's; the server no longer has the old ones anyway.
const BUILD_ASSETS_PATH = "/assets/gameplan/frontend/assets/";

async function deleteOldBuildAssets(currentUrls) {
  const current = new Set(
    currentUrls.map((url) => new URL(url, self.location.origin).pathname),
  );
  const cache = await caches.open(ASSET_CACHE);
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

async function staleWhileRevalidate(request) {
  const cache = await caches.open(RUNTIME_CACHE);
  const cached = await cache.match(request);
  if (!self.navigator.onLine) return cached || Response.error();
  if (cached && isRecent(cached)) return cached;

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
