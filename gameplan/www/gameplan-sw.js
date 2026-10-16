const CACHE_PREFIX = "gameplan-readonly-offline";
const CACHE_VERSION = "v11";

/** Serializes user-cache mutations and invalidates responses started before a clear. */
const userCaches = {
  stateCache: `${CACHE_PREFIX}-state`,
  stateKey: "/__gameplan-offline-generation",
  lock: `${CACHE_PREFIX}-user-caches`,
  pending: Promise.resolve(),

  exclusive(operation) {
    const run = () =>
      self.navigator.locks
        ? self.navigator.locks.request(this.lock, operation)
        : operation();
    const pending = this.pending.then(run, run);
    this.pending = pending.catch(() => {});
    return pending;
  },

  generation() {
    return this.exclusive(async () => {
      const state = await caches.open(this.stateCache);
      const stored = await state.match(this.stateKey);
      if (stored) return stored.text();
      const generation = crypto.randomUUID();
      await state.put(this.stateKey, new Response(generation));
      return generation;
    });
  },

  write(generation, operation) {
    return this.exclusive(async () => {
      const state = await caches.open(this.stateCache);
      const current = await (await state.match(this.stateKey))?.text();
      if (!generation || generation !== current) return false;
      await operation();
      return true;
    });
  },

  async rotateGeneration() {
    const state = await caches.open(this.stateCache);
    await state.put(this.stateKey, new Response(crypto.randomUUID()));
  },

  clear() {
    return this.exclusive(async () => {
      await this.rotateGeneration();
      const names = (await caches.keys()).filter(
        (name) =>
          name.startsWith(`${CACHE_PREFIX}:`) && !name.endsWith(":assets"),
      );
      return (
        await Promise.all(names.map((name) => caches.delete(name)))
      ).every(Boolean);
    });
  },
};
const SHELL_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:shell`;
const ASSET_CACHE = `${CACHE_PREFIX}:${CACHE_VERSION}:assets`;
// Images are per user and cleared on logout; build files (ASSET_CACHE) are shared and kept.
// Keep these across builds, but separate from legacy workers' unguarded late writes.
const RUNTIME_CACHE = `${CACHE_PREFIX}:guarded:runtime`;
const DOWNLOAD_CACHE = `${CACHE_PREFIX}:guarded:downloads`;
const APP_SHELL_URL = "/g";
const OFFLINE_ASSET_MANIFEST_URL =
  "/assets/gameplan/frontend/gameplan-offline-assets.json";
const PRECACHE_URLS = [
  APP_SHELL_URL,
  "/assets/gameplan/manifest/site.webmanifest",
  "/assets/gameplan/manifest/icon-maskable-192.png",
  "/assets/gameplan/manifest/icon-maskable-512.png",
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
  event.waitUntil(cleanUnusedBuilds());
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

  if (
    type === "CACHE_GENERATION" ||
    type === "CLEAR_USER_CACHES" ||
    type === "CLEAR_USER_CACHES_V2"
  ) {
    const operation =
      type === "CACHE_GENERATION"
        ? userCaches.generation()
        : userCaches.clear();
    event.waitUntil(
      operation.then(
        (answer) => event.ports[0]?.postMessage(answer),
        (error) => {
          console.error("User-cache operation failed", error);
          event.ports[0]?.postMessage(null);
        },
      ),
    );
    return;
  }

  if (type === "CACHE_IMAGES" && Array.isArray(event.data.urls)) {
    event.waitUntil(cacheImages(event.data.urls, event.data.generation));
    return;
  }

  if (type === "FORGET_IMAGES" && Array.isArray(event.data.urls)) {
    event.waitUntil(forgetImages(event.data.urls, event.data.generation));
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
    return;
  }

  if (type === "CLEAN_UNUSED_BUILDS") {
    event.waitUntil(cleanUnusedBuilds());
  }
});

async function warmShellCache() {
  if (!(await cacheBuild())) throw new Error("Offline build is incomplete");
  const generation = await userCaches.generation();
  let cache;
  const current = await userCaches.write(generation, async () => {
    cache = await caches.open(SHELL_CACHE);
  });
  if (!current) return;
  if (!(await saveAll(cache, PRECACHE_URLS, generation)))
    throw new Error("Offline shell is incomplete");
}

async function hasOpenGameplanPages() {
  const clients = await self.clients.matchAll({
    type: "window",
    includeUncontrolled: true,
  });
  return clients.some((client) =>
    client.url.startsWith(`${self.location.origin}/g`),
  );
}

async function deleteOldCaches() {
  const pagesOpen = await hasOpenGameplanPages();
  const currentCaches = new Set([
    SHELL_CACHE,
    ASSET_CACHE,
    RUNTIME_CACHE,
    DOWNLOAD_CACHE,
    userCaches.stateCache,
  ]);
  const names = await caches.keys();
  const oldAssetCaches = names
    .filter(
      (name) =>
        name.startsWith(CACHE_PREFIX) &&
        !currentCaches.has(name) &&
        name.endsWith(":assets"),
    )
    .sort();
  const keepCache =
    pagesOpen && oldAssetCaches.length
      ? oldAssetCaches[oldAssetCaches.length - 1]
      : null;

  await Promise.all(
    names
      .filter(
        (name) =>
          name.startsWith(CACHE_PREFIX) &&
          !currentCaches.has(name) &&
          name !== keepCache,
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
  const generation = await userCaches.generation();
  try {
    const response = await fetch(event.request);
    if (isHtmlResponse(response)) {
      event.waitUntil(refreshShell(response.clone(), generation));
    }
    return response;
  } catch {
    const cache = await caches.open(SHELL_CACHE);
    const cachedRequest = await cache.match(event.request);
    const cachedShell = await cache.match(APP_SHELL_URL);
    return cachedRequest || cachedShell || Response.error();
  }
}

async function refreshShell(response, generation) {
  if (!(await cacheBuild())) return;
  await userCaches.write(generation, async () => {
    const cache = await caches.open(SHELL_CACHE);
    await cache.put(APP_SHELL_URL, response);
  });
}

/** A shell is usable only once all of its build files are cached. */
async function cacheBuild() {
  try {
    const response = await fetch(OFFLINE_ASSET_MANIFEST_URL, {
      cache: "no-cache",
    });
    if (!isCacheableResponse(response)) return false;
    const urls = await response.json();
    if (!Array.isArray(urls) || !urls.length) return false;
    const cache = await caches.open(ASSET_CACHE);
    const saved = await saveAll(cache, urls.filter(isAssetUrl));
    if (saved) {
      const manifest = await cache.match(OFFLINE_ASSET_MANIFEST_URL);
      if (
        manifest &&
        JSON.stringify(await manifest.clone().json()) !== JSON.stringify(urls)
      ) {
        await cache.put(PREVIOUS_MANIFEST_KEY, manifest);
      }
      await cache.put(
        OFFLINE_ASSET_MANIFEST_URL,
        new Response(JSON.stringify(urls), {
          headers: { "content-type": "application/json" },
        }),
      );
      await deleteOldBuildAssets(cache, urls);
      await deleteOldCaches();
    }
    return saved;
  } catch {
    return false;
  }
}

/** Saves `url` into `cache` unless it is already there; a failure waits for the next try. */
async function save(cache, url, generation) {
  const request = new Request(url, { credentials: "include" });
  try {
    if (await cache.match(request)) return true;
    const response = await fetch(request);
    if (isCacheableResponse(response)) {
      if (generation)
        await userCaches.write(generation, () => cache.put(request, response));
      else await cache.put(request, response);
      return true;
    }
  } catch {
    // Offline, or the server refused it: the next visit or sync tries again.
  }
  return false;
}

/** A few at a time, so a first visit or download doesn't request everything at once. */
async function saveAll(cache, urls, generation) {
  const queue = [...urls];
  const saved = [];
  const next = async () => {
    while (queue.length)
      saved.push(await save(cache, queue.shift(), generation));
  };
  await Promise.all(Array.from({ length: FETCHES_AT_ONCE }, next));
  return saved.every(Boolean);
}

// Images of downloaded discussions, and custom emojis (offlineDownloads.ts).
async function cacheImages(urls, generation) {
  let cache;
  const current = await userCaches.write(generation, async () => {
    cache = await caches.open(DOWNLOAD_CACHE);
  });
  if (!current) return;
  await saveAll(cache, urls.filter(isUploadedFileUrl), generation);
  // The settings show what the downloads weigh, and these are part of it.
  for (const client of await self.clients.matchAll()) {
    client.postMessage({ type: "IMAGES_SAVED" });
  }
}

async function forgetImages(urls, generation) {
  await userCaches.write(generation, async () => {
    // Cancel older image requests before removing their cached copies.
    await userCaches.rotateGeneration();
    const imageCaches = await Promise.all(
      [DOWNLOAD_CACHE, RUNTIME_CACHE].map((name) => caches.open(name)),
    );
    await Promise.all(
      urls
        .filter(isUploadedFileUrl)
        .flatMap((url) => imageCaches.map((cache) => cache.delete(url))),
    );
  });
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
// ASSET_CACHE. Keep only what active pages need, and remove unused builds once they close.
const BUILD_ASSETS_PATH = "/assets/gameplan/frontend/assets/";
const PREVIOUS_MANIFEST_KEY =
  "/assets/gameplan/frontend/__previous-manifest.json";

async function deleteOldBuildAssets(cache, currentUrls) {
  const pagesOpen = await hasOpenGameplanPages();
  const currentSet = new Set(
    currentUrls.map((url) => new URL(url, self.location.origin).pathname),
  );

  let retainedSet = currentSet;
  if (pagesOpen) {
    let previousUrls = [];
    try {
      const match = await cache.match(PREVIOUS_MANIFEST_KEY);
      if (match) previousUrls = await match.json();
    } catch {
      // Manifest was unreadable or missing.
    }
    retainedSet = new Set([
      ...currentSet,
      ...previousUrls.map((url) => new URL(url, self.location.origin).pathname),
    ]);
  }

  const requests = await cache.keys();
  await Promise.all(
    requests
      .filter((request) => {
        const { pathname } = new URL(request.url);
        return (
          pathname.startsWith(BUILD_ASSETS_PATH) && !retainedSet.has(pathname)
        );
      })
      .map((request) => cache.delete(request)),
  );
}

async function cleanUnusedBuilds() {
  await deleteOldCaches();
  const cache = await caches.open(ASSET_CACHE);
  const manifest = await cache.match(OFFLINE_ASSET_MANIFEST_URL);
  if (manifest) {
    try {
      const urls = await manifest.json();
      if (Array.isArray(urls)) {
        await deleteOldBuildAssets(cache, urls);
      }
    } catch {
      // Manifest unreadable.
    }
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(ASSET_CACHE);
  // Old tabs still request their build's hashed chunks after a new worker takes over.
  const cached = await caches.match(request);
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
  const generation = await userCaches.generation();
  const request = event.request;
  // Retired workers can still finish a fetch. Never read their old media buckets.
  const cached =
    (await caches.match(request, { cacheName: DOWNLOAD_CACHE })) ||
    (await caches.match(request, { cacheName: RUNTIME_CACHE }));
  if (!self.navigator.onLine) return cached || Response.error();
  if (cached && isRecent(cached)) return cached;

  const fetched = fetch(request)
    .then((response) => {
      if (isCacheableResponse(response)) {
        event.waitUntil(saveBrowsed(request, response.clone(), generation));
      }
      return response;
    })
    .catch(() => null);

  return cached || (await fetched) || Response.error();
}

/** Keeps the newest MAX_BROWSED_IMAGES, oldest out first. */
async function saveBrowsed(request, response, generation) {
  await userCaches.write(generation, async () => {
    const cache = await caches.open(RUNTIME_CACHE);
    await cache.put(request, response);
    const keys = await cache.keys();
    await Promise.all(
      keys
        .slice(0, Math.max(0, keys.length - MAX_BROWSED_IMAGES))
        .map((key) => cache.delete(key)),
    );
  });
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
