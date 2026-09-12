// Shared helpers for the offline MVP Playwright suite (plain scripts, no @playwright/test).
// Originally a throwaway harness at /tmp/offline-mvp/pw; migrated here so it survives
// reboots and can gate regressions (see README.md).
const path = require('path')
const fs = require('fs')
const { chromium, request: pwRequest } = require('playwright')
const {
  BASE,
  EMAIL,
  PWD,
  EMAIL2,
  PWD2,
  FULL_NAME,
  FULL_NAME2,
  URLS,
  PEOPLE,
  SHOTS_DIR,
  RESULTS_DIR,
} = require('./config')

fs.mkdirSync(SHOTS_DIR, { recursive: true })
fs.mkdirSync(RESULTS_DIR, { recursive: true })

async function newLoggedInContextAs(browser, usr, pwd, contextOptions = {}) {
  const context = await browser.newContext(contextOptions)
  const loginResp = await context.request.post(`${BASE}/api/method/login`, {
    form: { usr, pwd },
  })
  if (!loginResp.ok()) {
    throw new Error(`login failed: ${loginResp.status()} ${await loginResp.text()}`)
  }
  const page = await context.newPage()
  const consoleErrors = []
  const pageErrors = []
  const prefetchLog = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text())
    if (msg.text().includes('[offline-prefetch]')) prefetchLog.push(msg.text())
  })
  page.on('pageerror', (err) => {
    pageErrors.push(String(err))
  })
  return { context, page, consoleErrors, pageErrors, prefetchLog }
}

async function newLoggedInContext(browser) {
  return newLoggedInContextAs(browser, EMAIL, PWD)
}

/**
 * Logs in as a second, already-authenticated identity within the SAME browser context
 * (same IndexedDB/localStorage/Cache Storage origin) — used by US7b to simulate a second
 * person using the same shared computer right after the first. Reuses the context's
 * cookie jar (context.request.post sets the cookie on the context), so the existing
 * `page` picks up the new session on its next navigation.
 */
async function loginAsInSameContext(context, page, usr, pwd) {
  const loginResp = await context.request.post(`${BASE}/api/method/login`, {
    form: { usr, pwd },
  })
  if (!loginResp.ok()) {
    throw new Error(`login failed: ${loginResp.status()} ${await loginResp.text()}`)
  }
  // The app's own guardAgainstUserSwitch (frontend/src/offline.ts) only runs at module
  // boot, so a fresh navigation is required for it to see the new user_id cookie.
  await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
  // `/g` client-side redirects to the community's discussions route once the app has
  // hydrated enough to know where to send you (post-327d7ae3, that redirect itself
  // waits on cache hydration under unreliable network). Wait for it to actually land
  // before the caller issues its own page.goto() — otherwise the in-flight SPA redirect
  // can still be settling when the next real navigation starts, and Playwright reports
  // that next goto() as "interrupted by another navigation" to the redirect's target.
  await page.waitForURL(/\/g\/community\//, { timeout: 10000 }).catch(() => {})
}

/** Opens the AppRail user-avatar dropdown (bottom-left) and clicks "Log out" — the same
 *  UI path a real user takes (UserDropdown.vue -> session.logout.submit(), see
 *  data/session.ts), so this also exercises the offline-cache-clear side effect under
 *  test rather than bypassing it with a raw API call. Selector is the avatar trigger
 *  button's own template classes (AppRail.vue) since the avatar itself may render either
 *  an <img> or an initials div depending on whether the user has a profile photo. */
async function logoutViaUI(page) {
  const trigger = page.locator('button.rounded-full.size-7').last()
  await trigger.click({ timeout: 8000 })
  await page.getByRole('menuitem', { name: 'Log out' }).click({ timeout: 8000 })
}

/** Reads idb-keyval's default store (IndexedDB db `keyval-store`, object store `keyval`)
 *  — frappe-ui's shared backing store for useList/useCall/useDoc caches (see offline.ts's
 *  clearOfflineCaches doc comment). Opening a DB that doesn't exist yet is harmless (it
 *  just creates an empty one with no object stores, same as p3.js already relies on). */
async function idbKeyvalKeys(page) {
  return page.evaluate(
    () =>
      new Promise((resolve) => {
        const req = indexedDB.open('keyval-store')
        req.onsuccess = () => {
          const db = req.result
          if (!db.objectStoreNames.contains('keyval')) {
            db.close()
            resolve([])
            return
          }
          const tx = db.transaction('keyval', 'readonly')
          const keysReq = tx.objectStore('keyval').getAllKeys()
          keysReq.onsuccess = () => {
            db.close()
            resolve(keysReq.result)
          }
          keysReq.onerror = () => {
            db.close()
            resolve([])
          }
        }
        req.onerror = () => resolve([])
      }),
  )
}

/** Reads draftStore.ts's custom idb-keyval store (`gameplan-drafts` db, `records` store). */
async function draftStoreKeys(page) {
  return page.evaluate(
    () =>
      new Promise((resolve) => {
        const req = indexedDB.open('gameplan-drafts')
        req.onsuccess = () => {
          const db = req.result
          if (!db.objectStoreNames.contains('records')) {
            db.close()
            resolve([])
            return
          }
          const tx = db.transaction('records', 'readonly')
          const keysReq = tx.objectStore('records').getAllKeys()
          keysReq.onsuccess = () => {
            db.close()
            resolve(keysReq.result)
          }
          keysReq.onerror = () => {
            db.close()
            resolve([])
          }
        }
        req.onerror = () => resolve([])
      }),
  )
}

/** Cache Storage bucket names the SW created — see gameplan-sw.js's SHELL_CACHE/
 *  ASSET_CACHE/RUNTIME_CACHE naming (`gameplan-readonly-offline:<version>:<kind>`). */
async function cacheStorageNames(page) {
  return page.evaluate(() => (typeof caches !== 'undefined' ? caches.keys() : []))
}

async function lastSeenUserFromStorage(page) {
  return page.evaluate(() => {
    try {
      return localStorage.getItem('gameplan:last-seen-user')
    } catch {
      return null
    }
  })
}

/**
 * Waits for data/offlinePrefetch.ts's `[offline-prefetch] done members=... profiles=...
 * bento=... avatars=...` console.debug line, by polling the `prefetchLog` array
 * `newLoggedInContext` populates. The prefetcher is idle-delayed (up to
 * IDLE_TIMEOUT_MS=10s) then fans out over every member with a small worker pool, so this
 * needs a generous timeout — callers should navigate to a lightweight page (the feed) and
 * just let it sit rather than doing other work while waiting.
 */
async function waitForPrefetchDone(prefetchLog, { timeoutMs = 45000, pollMs = 500 } = {}) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    const doneLine = prefetchLog.find((l) => l.includes('[offline-prefetch] done'))
    if (doneLine) {
      const m = doneLine.match(/members=(\d+)\s+profiles=(\d+)\s+bento=(\d+)\s+avatars=(\d+)/)
      return {
        sawDone: true,
        sawStartFirst: prefetchLog[0]?.includes('[offline-prefetch] start') ?? false,
        doneLine,
        counts: m
          ? {
              members: Number(m[1]),
              profiles: Number(m[2]),
              bento: Number(m[3]),
              avatars: Number(m[4]),
            }
          : null,
      }
    }
    await new Promise((r) => setTimeout(r, pollMs))
  }
  return {
    sawDone: false,
    sawStartFirst: prefetchLog[0]?.includes('[offline-prefetch] start') ?? false,
    doneLine: null,
    counts: null,
    log: [...prefetchLog],
  }
}

async function avatarInfo(page, scope = 'img') {
  return page.evaluate((sel) => {
    const imgs = Array.from(document.querySelectorAll(sel))
    return imgs.slice(0, 12).map((img) => ({
      src: img.src,
      complete: img.complete,
      naturalWidth: img.naturalWidth,
      broken: img.complete && img.naturalWidth === 0,
    }))
  }, scope)
}

/** Separate, independent auth context for API calls that must succeed while the
 * browser `page`/`context` is simulating offline (context.setOffline only affects
 * the page's network stack, not a wholly separate APIRequestContext, but per the
 * task brief we keep this fully separate for clarity and to avoid any doubt). */
async function newApiRequestContext() {
  const api = await pwRequest.newContext({ baseURL: BASE })
  const loginResp = await api.post('/api/method/login', {
    form: { usr: EMAIL, pwd: PWD },
  })
  if (!loginResp.ok()) {
    throw new Error(`API login failed: ${loginResp.status()} ${await loginResp.text()}`)
  }
  return api
}

async function warmup(page) {
  // Visit the three pages online, waiting for real content, then wait for the
  // service worker to finish installing so offline tests have a warm cache.
  const swBefore = await page.evaluate(() => ({
    hasSW: 'serviceWorker' in navigator,
    isSecureContext: window.isSecureContext,
  }))

  for (const url of [URLS.feed, URLS.spaceDiscussions, URLS.discussion]) {
    await page.goto(url, { waitUntil: 'load', timeout: 15000 })
    // `/g` itself client-side redirects to the community's discussions route once the
    // app has hydrated enough to know where to send you (post-327d7ae3, that redirect
    // waits on cache hydration under unreliable network, so it isn't always instant).
    // Let it land before starting the next goto() in this loop — otherwise, under load,
    // the in-flight SPA redirect can still be settling when the next real navigation
    // starts, and Playwright reports that next goto() as "interrupted by another
    // navigation" to the redirect's target (same race loginAsInSameContext guards
    // against for the US7b user-switch flow).
    if (url === URLS.feed) {
      await page.waitForURL(/\/g\/community\//, { timeout: 10000 }).catch(() => {})
    }
    await page.waitForTimeout(1000)
  }

  let swController = null
  let swReady = false
  let swReadyError = null
  try {
    swController = await page.evaluate(() => Boolean(navigator.serviceWorker.controller))
    await page.evaluate(() => navigator.serviceWorker.ready.then(() => true), { timeout: 10000 })
    swReady = true
  } catch (e) {
    swReadyError = String(e)
  }

  // Give the SW's warmLoadedAssets() postMessage (fired on load + a 3s follow-up
  // timer, see frontend/src/offline.ts) time to finish caching assets/shell.
  await page.waitForTimeout(4000)

  const swRegistrations = await page.evaluate(async () => {
    const regs = await navigator.serviceWorker.getRegistrations()
    return regs.map((r) => ({
      scope: r.scope,
      active: Boolean(r.active),
      activeState: r.active?.state,
    }))
  })

  return { ...swBefore, swController, swReady, swReadyError, swRegistrations }
}

async function shot(page, name) {
  const p = path.join(SHOTS_DIR, `${name}.png`)
  try {
    await page.screenshot({ path: p, fullPage: false, timeout: 8000 })
  } catch (e) {
    return null
  }
  return p
}

async function innerTextSafe(page, selector = '#app, body') {
  try {
    return await page.locator(selector).first().innerText({ timeout: 5000 })
  } catch (e) {
    try {
      return await page.evaluate(() => document.body?.innerText?.slice(0, 2000) || '')
    } catch {
      return ''
    }
  }
}

async function appRootInfo(page) {
  return page.evaluate(() => {
    const app = document.querySelector('#app')
    return {
      appExists: Boolean(app),
      appChildCount: app ? app.childElementCount : 0,
      bodyText: document.body.innerText.slice(0, 500),
      title: document.title,
    }
  })
}

function writeResult(story, obj) {
  const p = path.join(RESULTS_DIR, `${story}.json`)
  fs.writeFileSync(p, JSON.stringify(obj, null, 2))
  return p
}

module.exports = {
  BASE,
  EMAIL,
  PWD,
  EMAIL2,
  PWD2,
  FULL_NAME,
  FULL_NAME2,
  URLS,
  PEOPLE,
  SHOTS_DIR,
  RESULTS_DIR,
  newLoggedInContext,
  newLoggedInContextAs,
  loginAsInSameContext,
  logoutViaUI,
  idbKeyvalKeys,
  draftStoreKeys,
  cacheStorageNames,
  lastSeenUserFromStorage,
  newApiRequestContext,
  warmup,
  waitForPrefetchDone,
  avatarInfo,
  shot,
  innerTextSafe,
  appRootInfo,
  writeResult,
  chromium,
}
