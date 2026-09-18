const CACHE_PREFIX = "gameplan-readonly-offline";
const CACHE_VERSION = "v7";
const SHELL_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:shell`;
const ASSET_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:assets`;
// Avatars and other runtime images are user-visible content fetched by URL, with no
// user scoping (unlike the app's IndexedDB caches - see offline.ts's clearOfflineCaches).
// Keeping them in a separate bucket from ASSET_CACHE (hashed, content-addressed /assets
// build output, which is identical for every user) lets CLEAR_USER_CACHES below wipe the
// former on logout/user-switch without also evicting the latter.
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
  // No self.skipWaiting() here: when this install is replacing an already-active
  // worker (a deploy landing under an open tab), the new worker should sit in
  // `waiting` until the page confirms via SKIP_WAITING (offline.ts's update toast).
  // Skipping unconditionally would swap the controller under a running tab with no
  // warning. A first-ever install (no prior controller) activates regardless of this.
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
    // Round-4 finding: guardAgainstUserSwitch (offline.ts) clears SHELL_CACHE after a
    // detected user switch, and nothing repopulates it until the *next* successful
    // online navigation to /g. If the browser goes offline before that happens, even a
    // reload of the page already open fails with net::ERR_FAILED instead of the offline
    // UI. offline.ts posts this message right after that clear resolves, at a moment
    // it's known to be online (a user just logged in) - warmShellCache() is already
    // best-effort per-URL, so this is harmless if connectivity drops mid-fetch.
    // Deliberately a separate message from CLEAR_USER_CACHES (not folded into
    // clearUserCaches itself): a plain logout also clears via CLEAR_USER_CACHES, and an
    // empty shell cache is the intended post-logout state there.
    event.waitUntil(warmShellCache());
  }
});

// Shared-computer safety (see clearOfflineCaches in offline.ts, called on logout and on
// detecting a different session user at boot): wipe everything that can hold the
// previous user's content. The app shell HTML and runtime images/files are the only
// user-visible things this worker caches - ASSET_CACHE (hashed /assets build output) is
// content-addressed and identical for every user, so it's left alone.
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

// Offline downloads (offlineDownloads.ts): images inside downloaded discussions and custom
// emojis. Kept in the runtime cache with images seen while browsing, so logout clears them.
const IMAGE_FETCHES_AT_ONCE = 4;

async function cacheImages(urls) {
  const cache = await caches.open(RUNTIME_CACHE);
  const queue = urls.filter(isUploadedFileUrl);
  // A few at a time, so a first download doesn't send every image request at once.
  const next = async () => {
    while (queue.length) {
      const request = new Request(queue.shift(), { credentials: "include" });
      try {
        if (await cache.match(request)) continue;
        const response = await fetch(request);
        if (isCacheableResponse(response)) await cache.put(request, response);
      } catch {
        // The next sync, or viewing the image online, tries again.
      }
    }
  };
  await Promise.all(Array.from({ length: IMAGE_FETCHES_AT_ONCE }, next));
}

async function forgetImages(urls) {
  const cache = await caches.open(RUNTIME_CACHE);
  await Promise.all(urls.filter(isUploadedFileUrl).map((url) => cache.delete(url)));
}

function isUploadedFileUrl(url) {
  try {
    const { origin, pathname } = new URL(url, self.location.origin);
    return (
      origin === self.location.origin &&
      (pathname.startsWith("/files/") || pathname.startsWith("/private/files/"))
    );
  } catch {
    return false;
  }
}

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
  const cache = await caches.open(RUNTIME_CACHE);
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
