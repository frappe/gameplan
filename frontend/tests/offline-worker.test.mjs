import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { randomUUID } from 'node:crypto'
import test from 'node:test'
import vm from 'node:vm'

const origin = 'https://gameplan.test'
const workerSource = readFileSync(
  new URL('../../gameplan/www/gameplan-sw.js', import.meta.url),
  'utf8',
)
const prefix = 'gameplan-readonly-offline'

function deferred() {
  let resolve
  const promise = new Promise((done) => {
    resolve = done
  })
  return { promise, resolve }
}

// Deleting a named cache detaches existing handles, as the browser Cache API does.
function storage() {
  const buckets = new Map()
  const key = (request) => new URL(typeof request === 'string' ? request : request.url, origin).href
  return {
    async open(name) {
      if (!buckets.has(name)) buckets.set(name, new Map())
      const bucket = buckets.get(name)
      return {
        match: async (request) => bucket.get(key(request))?.clone(),
        put: async (request, response) => bucket.set(key(request), response.clone()),
        delete: async (request) => bucket.delete(key(request)),
        keys: async () => [...bucket.keys()].map((url) => new Request(url)),
      }
    },
    keys: async () => [...buckets.keys()],
    delete: async (name) => buckets.delete(name),
    async match(request, options = {}) {
      const entries = options.cacheName ? [buckets.get(options.cacheName)] : buckets.values()
      for (const bucket of entries) {
        if (!bucket) continue
        const response = bucket.get(key(request))
        if (response) return response.clone()
      }
    },
  }
}

function worker(
  caches,
  fetch = async () => {
    throw new Error('Unexpected fetch')
  },
) {
  const handlers = new Map()
  const context = vm.createContext({
    caches,
    fetch,
    console,
    URL,
    Response,
    crypto: { randomUUID },
    Request: class extends Request {
      constructor(url, options) {
        super(new URL(url, origin), options)
      }
    },
    self: {
      location: { origin },
      navigator: { onLine: true },
      clients: { matchAll: async () => [] },
      addEventListener: (type, handler) => handlers.set(type, handler),
    },
  })
  vm.runInContext(workerSource, context)
  return {
    evaluate: (source) => vm.runInContext(source, context),
    context,
    message(data) {
      let pending
      let answer
      handlers.get('message')({
        data,
        ports: [
          {
            postMessage: (value) => {
              answer = value
            },
          },
        ],
        waitUntil: (operation) => {
          pending = operation
        },
      })
      return Promise.resolve(pending).then(() => answer)
    },
  }
}

function image() {
  const response = new Response('private image')
  Object.defineProperty(response, 'type', { value: 'basic' })
  return response
}

test('a browsing image response arriving after cleanup cannot recreate the cache', async () => {
  const caches = storage()
  const started = deferred()
  const response = deferred()
  const current = worker(caches, () => {
    started.resolve()
    return response.promise
  })
  const writes = []
  current.context.event = {
    request: new Request(`${origin}/private/files/browsed.png`),
    waitUntil: (pending) => writes.push(pending),
  }
  const fetched = current.evaluate('staleWhileRevalidate(event)')
  await started.promise
  assert.equal(await current.message({ type: 'CLEAR_USER_CACHES' }), true)
  response.resolve(image())
  await fetched
  await Promise.all(writes)
  assert.equal(await caches.match('/private/files/browsed.png'), undefined)
  assert.equal((await caches.keys()).includes(current.evaluate('RUNTIME_CACHE')), false)
})

for (const type of ['CLEAR_USER_CACHES', 'FORGET_IMAGES']) {
  test(`an in-flight downloaded image cannot return after ${type}`, async () => {
    const caches = storage()
    const started = deferred()
    const response = deferred()
    const current = worker(caches, () => {
      started.resolve()
      return response.promise
    })
    const generation = await current.message({ type: 'CACHE_GENERATION' })
    const downloaded = current.message({
      type: 'CACHE_IMAGES',
      urls: ['/private/files/downloaded.png'],
      generation,
    })
    await started.promise
    await current.message({ type, urls: ['/private/files/downloaded.png'], generation })
    response.resolve(image())
    await downloaded
    assert.equal(await caches.match('/private/files/downloaded.png'), undefined)
  })
}

test('a queued image batch from the old generation is ignored after cleanup', async () => {
  const caches = storage()
  const current = worker(caches)
  const generation = await current.message({ type: 'CACHE_GENERATION' })
  await current.message({ type: 'CLEAR_USER_CACHES' })
  await current.message({ type: 'CACHE_IMAGES', urls: ['/private/files/queued.png'], generation })
  assert.equal((await caches.keys()).includes(current.evaluate('DOWNLOAD_CACHE')), false)
})

test('the generation survives a worker restart and current images still cache', async () => {
  const caches = storage()
  const original = worker(caches)
  const oldGeneration = await original.message({ type: 'CACHE_GENERATION' })
  await original.message({ type: 'CLEAR_USER_CACHES' })
  const generation = await original.message({ type: 'CACHE_GENERATION' })
  const restarted = worker(caches, async () => image())
  assert.equal(await restarted.message({ type: 'CACHE_GENERATION' }), generation)
  assert.notEqual(generation, oldGeneration)
  await restarted.message({
    type: 'CACHE_IMAGES',
    urls: ['/private/files/old.png'],
    generation: oldGeneration,
  })
  await restarted.message({
    type: 'CACHE_IMAGES',
    urls: ['/private/files/current.png'],
    generation,
  })
  assert.equal(await caches.match('/private/files/old.png'), undefined)
  assert.equal(await (await caches.match('/private/files/current.png')).text(), 'private image')
})

test('forgetting a revoked image removes both copies and leaves other images', async () => {
  const caches = storage()
  const current = worker(caches)
  const generation = await current.message({ type: 'CACHE_GENERATION' })
  for (const name of current.evaluate('[RUNTIME_CACHE, DOWNLOAD_CACHE]')) {
    const cache = await caches.open(name)
    await cache.put('/private/files/revoked.png', image())
    await cache.put('/private/files/readable.png', image())
  }
  await current.message({ type: 'FORGET_IMAGES', urls: ['/private/files/revoked.png'], generation })
  assert.equal(await caches.match('/private/files/revoked.png'), undefined)
  assert.equal(await (await caches.match('/private/files/readable.png')).text(), 'private image')
})

test('cleanup waits for a cache mutation and preserves public build files', async () => {
  const caches = storage()
  const current = worker(caches)
  const generation = await current.message({ type: 'CACHE_GENERATION' })
  const started = deferred()
  const finish = deferred()
  current.context.generation = generation
  current.context.pause = async () => {
    started.resolve()
    await finish.promise
  }
  const assets = await caches.open(current.evaluate('ASSET_CACHE'))
  await assets.put('/assets/app.js', new Response('public build'))
  const saving = current.evaluate(`userCaches.write(generation, async () => {
    await pause();
    const cache = await caches.open(RUNTIME_CACHE);
    await cache.put('/private/files/saving.png', new Response('private image'));
  })`)
  await started.promise
  const cleared = current.message({ type: 'CLEAR_USER_CACHES' })
  finish.resolve()
  await saving
  assert.equal(await cleared, true)
  assert.equal(await caches.match('/private/files/saving.png'), undefined)
  assert.equal(await (await caches.match('/assets/app.js')).text(), 'public build')
})

test('an upgraded worker cannot serve a late image from a legacy worker', async () => {
  const caches = storage()
  const current = worker(caches)
  await current.message({ type: 'CLEAR_USER_CACHES' })
  // A retiring worker finishes its old request after the new worker cleared the caches.
  const legacy = await caches.open(`${prefix}:runtime`)
  await legacy.put('/private/files/legacy.png', image())
  current.context.self.navigator.onLine = false
  current.context.event = {
    request: new Request(`${origin}/private/files/legacy.png`),
    waitUntil() {},
  }
  assert.equal((await current.evaluate('staleWhileRevalidate(event)')).type, 'error')

  const downloads = await caches.open(current.evaluate('DOWNLOAD_CACHE'))
  await downloads.put('/private/files/legacy.png', new Response('current account image'))
  assert.equal(
    await (await current.evaluate('staleWhileRevalidate(event)')).text(),
    'current account image',
  )
})

test('old build chunks remain readable while a page still uses them', async () => {
  const caches = storage()
  const current = worker(caches)
  const older = await caches.open(`${prefix}:v8:assets`)
  await older.put('/assets/gameplan/frontend/assets/v8-route.js', new Response('v8 route'))
  const old = await caches.open(`${prefix}:v9:assets`)
  await old.put('/assets/gameplan/frontend/assets/old-route.js', new Response('old route'))
  current.context.self.clients.matchAll = async () => [{ url: `${origin}/g/community/acme` }]
  await current.evaluate('deleteOldCaches()')
  current.context.request = new Request(`${origin}/assets/gameplan/frontend/assets/old-route.js`)
  assert.equal(await (await current.evaluate('cacheFirst(request)')).text(), 'old route')
  // Older asset caches beyond the immediately preceding one are purged even if a page is open
  assert.equal(await caches.match('/assets/gameplan/frontend/assets/v8-route.js'), undefined)

  current.context.self.clients.matchAll = async () => []
  await current.evaluate('deleteOldCaches()')
  assert.equal(await caches.match('/assets/gameplan/frontend/assets/old-route.js'), undefined)
})

test('an incomplete build keeps the working shell and its assets', async () => {
  const caches = storage()
  const current = worker(caches, async (request) => {
    if (String(request).includes('gameplan-offline-assets.json')) {
      const response = new Response(JSON.stringify(['/assets/gameplan/frontend/assets/new.js']))
      Object.defineProperty(response, 'type', { value: 'basic' })
      return response
    }
    throw new Error('Interrupted deployment')
  })
  const shell = await caches.open(current.evaluate('SHELL_CACHE'))
  await shell.put('/g', new Response('working shell'))
  const assets = await caches.open(current.evaluate('ASSET_CACHE'))
  await assets.put('/assets/gameplan/frontend/assets/old.js', new Response('working route'))
  current.context.response = new Response('new shell')
  current.context.generation = await current.message({ type: 'CACHE_GENERATION' })
  await current.evaluate('refreshShell(response, generation)')
  assert.equal(await (await shell.match('/g')).text(), 'working shell')
  assert.equal(
    await (await assets.match('/assets/gameplan/frontend/assets/old.js')).text(),
    'working route',
  )
  await assert.rejects(current.evaluate('warmShellCache()'), /Offline build is incomplete/)
})

test('previous build files remain while pages are open, but older builds and closed pages get cleared', async () => {
  const caches = storage()
  const current = worker(caches)
  const assets = await caches.open(current.evaluate('ASSET_CACHE'))

  // Initial build deployed and cached
  await assets.put('/assets/gameplan/frontend/assets/build1.js', new Response('build 1'))
  current.context.cache = assets
  current.context.urls = ['/assets/gameplan/frontend/assets/build1.js']
  await current.evaluate('deleteOldBuildAssets(cache, urls)')

  // Deploy build 2 with a tab open: build 1 must be kept for the open page
  current.context.self.clients.matchAll = async () => [{ url: `${origin}/g/feed` }]
  await assets.put('/assets/gameplan/frontend/assets/build2.js', new Response('build 2'))
  current.context.urls = ['/assets/gameplan/frontend/assets/build2.js']
  await current.evaluate('deleteOldBuildAssets(cache, urls)')
  current.context.req1 = new Request(`${origin}/assets/gameplan/frontend/assets/build1.js`)
  current.context.req2 = new Request(`${origin}/assets/gameplan/frontend/assets/build2.js`)
  assert.equal(await (await current.evaluate('cacheFirst(req1)')).text(), 'build 1')
  assert.equal(await (await current.evaluate('cacheFirst(req2)')).text(), 'build 2')

  // Deploy build 3 with page still open: build 1 should now be dropped, build 2 retained
  await assets.put('/assets/gameplan/frontend/assets/build3.js', new Response('build 3'))
  current.context.urls = ['/assets/gameplan/frontend/assets/build3.js']
  await current.evaluate('deleteOldBuildAssets(cache, urls)')
  assert.equal(await caches.match('/assets/gameplan/frontend/assets/build1.js'), undefined)
  assert.equal(await (await current.evaluate('cacheFirst(req2)')).text(), 'build 2')
  current.context.req3 = new Request(`${origin}/assets/gameplan/frontend/assets/build3.js`)
  assert.equal(await (await current.evaluate('cacheFirst(req3)')).text(), 'build 3')

  // Pages close: cleanUnusedBuilds clears build 2, retaining only build 3
  current.context.self.clients.matchAll = async () => []
  await current.evaluate('deleteOldBuildAssets(cache, urls)')
  assert.equal(await caches.match('/assets/gameplan/frontend/assets/build2.js'), undefined)
  assert.equal(await (await current.evaluate('cacheFirst(req3)')).text(), 'build 3')
})

test('a successful build saves manifest and assets into cache', async () => {
  const caches = storage()
  const current = worker(caches, async (request) => {
    const url = String(request.url || request)
    if (url.includes('gameplan-offline-assets.json')) {
      const response = new Response(JSON.stringify(['/assets/gameplan/frontend/assets/app.js']))
      Object.defineProperty(response, 'type', { value: 'basic' })
      return response
    }
    if (url.includes('/assets/gameplan/frontend/assets/app.js')) {
      const response = new Response('console.log("app")')
      Object.defineProperty(response, 'type', { value: 'basic' })
      return response
    }
    throw new Error('Not found: ' + url)
  })
  const result = await current.evaluate('cacheBuild()')
  assert.equal(result, true)
  const assetCache = await caches.open(current.evaluate('ASSET_CACHE'))
  const manifest = await assetCache.match(current.evaluate('OFFLINE_ASSET_MANIFEST_URL'))
  assert.ok(manifest)
  assert.deepEqual(await manifest.json(), ['/assets/gameplan/frontend/assets/app.js'])
})
