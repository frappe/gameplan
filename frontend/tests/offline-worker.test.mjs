import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { randomUUID } from 'node:crypto'
import test from 'node:test'
import vm from 'node:vm'
import { setImmediate } from 'node:timers/promises'

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
  const manifestUrl = current.evaluate('OFFLINE_ASSET_MANIFEST_URL')
  const previousKey = current.evaluate('PREVIOUS_MANIFEST_KEY')
  const manifest = JSON.stringify(['/assets/gameplan/frontend/assets/old.js'])
  const previous = JSON.stringify(['/assets/gameplan/frontend/assets/older.js'])
  await assets.put(manifestUrl, new Response(manifest))
  await assets.put(previousKey, new Response(previous))
  current.context.response = new Response('new shell')
  current.context.generation = await current.message({ type: 'CACHE_GENERATION' })
  await current.evaluate('refreshShell(response, generation)')
  assert.equal(await (await shell.match('/g')).text(), 'working shell')
  assert.equal(
    await (await assets.match('/assets/gameplan/frontend/assets/old.js')).text(),
    'working route',
  )
  await assert.rejects(current.evaluate('warmShellCache()'), /Offline build is incomplete/)
  assert.equal(await (await assets.match(manifestUrl)).text(), manifest)
  assert.equal(await (await assets.match(previousKey)).text(), previous)
})

test('repeated build caching and pagehide cleanup retain the previous distinct build', async () => {
  const caches = storage()
  let build = 1
  const assetUrl = (version) => `/assets/gameplan/frontend/assets/build${version}.js`
  const current = worker(caches, async (request) => {
    const url = String(request.url || request)
    const response = new Response(
      url.includes('gameplan-offline-assets.json')
        ? JSON.stringify([assetUrl(build)])
        : `build ${build}`,
    )
    Object.defineProperty(response, 'type', { value: 'basic' })
    return response
  })
  const assets = await caches.open(current.evaluate('ASSET_CACHE'))
  assert.equal(await current.evaluate('cacheBuild()'), true)
  current.context.self.clients.matchAll = async () => [{ url: `${origin}/g/feed` }]
  build = 2
  assert.equal(await current.evaluate('cacheBuild()'), true)

  // Repeated navigation and pagehide from another tab must not advance the predecessor.
  for (let repeat = 0; repeat < 2; repeat++) {
    assert.equal(await current.evaluate('cacheBuild()'), true)
    await current.message({ type: 'CLEAN_UNUSED_BUILDS' })
    assert.equal(await (await assets.match(assetUrl(1)))?.text(), 'build 1')
    assert.equal(await (await assets.match(assetUrl(2)))?.text(), 'build 2')
    assert.deepEqual(await (await assets.match(current.evaluate('PREVIOUS_MANIFEST_KEY'))).json(), [
      assetUrl(1),
    ])
  }

  // A distinct deployment drops the oldest build, keeping only current and predecessor.
  build = 3
  assert.equal(await current.evaluate('cacheBuild()'), true)
  await current.evaluate('cleanUnusedBuilds()')
  assert.equal(await assets.match(assetUrl(1)), undefined)
  assert.equal(await (await assets.match(assetUrl(2))).text(), 'build 2')
  assert.equal(await (await assets.match(assetUrl(3))).text(), 'build 3')

  current.context.self.clients.matchAll = async () => []
  await current.message({ type: 'CLEAN_UNUSED_BUILDS' })
  assert.equal(await assets.match(assetUrl(2)), undefined)
  assert.equal(await (await assets.match(assetUrl(3))).text(), 'build 3')
})

for (const operation of ['cleanup', 'another build']) {
  test(`${operation} waits for a partially downloaded build without blocking logout`, async () => {
    const caches = storage()
    const firstSaved = deferred()
    const finish = deferred()
    let build = 1
    const assetUrl = (version, chunk) =>
      `/assets/gameplan/frontend/assets/build${version}-${chunk}.js`
    const current = worker(caches, async (request) => {
      const url = String(request.url || request)
      if (url.includes('gameplan-offline-assets.json')) {
        const response = new Response(JSON.stringify([assetUrl(build, 1), assetUrl(build, 2)]))
        Object.defineProperty(response, 'type', { value: 'basic' })
        return response
      }
      if (url.endsWith('build2-2.js')) await finish.promise
      const response = new Response(url)
      Object.defineProperty(response, 'type', { value: 'basic' })
      return response
    })
    const assets = await caches.open(current.evaluate('ASSET_CACHE'))
    const open = caches.open
    caches.open = async (name) => {
      const cache = await open(name)
      const put = cache.put
      cache.put = async (request, response) => {
        await put(request, response)
        if (String(request.url || request).endsWith('build2-1.js')) firstSaved.resolve()
      }
      return cache
    }
    assert.equal(await current.evaluate('cacheBuild()'), true)
    current.context.self.clients.matchAll = async () => [{ url: `${origin}/g/feed` }]
    build = 2
    const saving = current.evaluate('cacheBuild()')
    await firstSaved.promise
    build = 3
    const competing =
      operation === 'cleanup'
        ? current.message({ type: 'CLEAN_UNUSED_BUILDS' })
        : current.evaluate('cacheBuild()')
    // Drain runnable cache operations while build 2's second response remains paused.
    await setImmediate()
    assert.equal(await current.message({ type: 'CLEAR_USER_CACHES' }), true)
    finish.resolve()
    assert.equal(await saving, true)
    await competing
    const manifest = await (
      await assets.match(current.evaluate('OFFLINE_ASSET_MANIFEST_URL'))
    ).json()
    const previous = await (await assets.match(current.evaluate('PREVIOUS_MANIFEST_KEY'))).json()
    for (const url of [...manifest, ...previous]) {
      assert.ok(await assets.match(url), `Missing committed build asset: ${url}`)
    }
  })
}

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
