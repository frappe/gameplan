// US7a — Shared-computer safety, logout path: after a real UI logout, every trace of the
// logged-out user's offline content should be gone from this browser (frappe-ui's shared
// idb-keyval store, and the service worker's SHELL_CACHE + RUNTIME_CACHE), so the next
// person on this machine can't read it — EXCEPT gameplan-drafts, which the task's Step 0
// policy adjustment keeps around on a plain logout (same person may log back in and expect
// their in-progress draft still there; useDraftSync already guards reads by `record.user`
// so leaving it isn't a leak). See frontend/src/offline.ts's clearOfflineCaches /
// data/draftStore.ts's clearDraftStore.
const {
  chromium,
  URLS,
  PEOPLE,
  EMAIL,
  newLoggedInContext,
  waitForPrefetchDone,
  logoutViaUI,
  idbKeyvalKeys,
  draftStoreKeys,
  cacheStorageNames,
  shot,
  writeResult,
} = require('./helpers')

const MEMBER = PEOPLE.visitedFully // 'maya-iyer'
const DRAFT_MARKER = `us7a-draft-${Date.now()}`

async function openComposer(page) {
  const addCommentBtn = page.locator('button:has-text("Add a comment")').first()
  if (await addCommentBtn.isVisible().catch(() => false)) {
    await addCommentBtn.click()
    await page.waitForTimeout(300)
  }
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors, prefetchLog } =
    await newLoggedInContext(browser)
  const result = { story: 'US7a', checks: [] }

  try {
    // Warm caches: People, a profile, and a discussion, plus give the background
    // prefetcher (data/offlinePrefetch.ts) and the SW's warmLoadedAssets a chance to run,
    // same as P1/P2's warmup pattern.
    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
    // `/g` client-side redirects to the community's discussions route once the app has
    // hydrated (post-327d7ae3, that redirect waits on cache hydration, so it isn't
    // always instant) — let it land before the next goto(), or that next navigation can
    // get reported as "interrupted by another navigation" to the redirect's target.
    await page.waitForURL(/\/g\/community\//, { timeout: 10000 }).catch(() => {})
    await page.waitForTimeout(1000)
    await page.goto(URLS.people, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1000)
    await page.goto(URLS.person(MEMBER), { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1500)
    await page.goto(URLS.discussion, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1500)

    try {
      await page.evaluate(() => navigator.serviceWorker.ready.then(() => true))
    } catch (e) {
      // best-effort
    }
    const prefetch = await waitForPrefetchDone(prefetchLog, { timeoutMs: 45000 })
    result.prefetch = prefetch
    await page.waitForTimeout(2000) // warmLoadedAssets() follow-up timer

    // Create a draft (comment composer, not submitted) so we can assert it survives a
    // plain logout below — the Step 0 policy this story is specifically verifying.
    let draftCreated = false
    try {
      await openComposer(page)
      const editor = page.locator('[contenteditable="true"]').last()
      await editor.click({ timeout: 5000 })
      await page.keyboard.type(DRAFT_MARKER, { delay: 10 })
      await page.waitForTimeout(500)
      draftCreated = true
    } catch (e) {
      result.draftCreateError = String(e)
    }

    result.preLogoutKeyvalKeys = await idbKeyvalKeys(page)
    result.preLogoutDraftKeys = draftCreated ? await draftStoreKeys(page) : null
    result.preLogoutCaches = await cacheStorageNames(page)

    result.checks.push({
      name: 'IndexedDB (keyval-store) has data before logout',
      pass: result.preLogoutKeyvalKeys.length > 0,
      symptom:
        result.preLogoutKeyvalKeys.length > 0
          ? `${result.preLogoutKeyvalKeys.length} key(s) present pre-logout`
          : 'keyval-store empty before logout — warmup did not populate any cache, test setup problem',
    })

    if (draftCreated) {
      result.checks.push({
        name: 'draft store has the new draft before logout',
        pass: result.preLogoutDraftKeys.length > 0,
        symptom:
          result.preLogoutDraftKeys.length > 0
            ? `${result.preLogoutDraftKeys.length} draft record(s) present pre-logout`
            : 'gameplan-drafts empty even after typing a comment — draft never persisted locally',
      })
    } else {
      result.checks.push({
        name: 'draft store has the new draft before logout',
        pass: null,
        symptom: `skipped — could not create a draft: ${result.draftCreateError}`,
      })
    }

    // Log out via the real UI path (UserDropdown.vue -> session.logout.submit()), so
    // this exercises the actual clearOfflineCaches side effect, not a bypass.
    let checkLogout = { name: 'logout via UI redirects to /login' }
    try {
      await logoutViaUI(page)
      await page.waitForURL('**/login**', { timeout: 10000 })
      checkLogout.pass = true
      checkLogout.symptom = `redirected to ${page.url()}`
    } catch (e) {
      checkLogout.pass = false
      checkLogout.symptom = `threw: ${e.message}`
      checkLogout.screenshot = await shot(page, 'us7a-logout-error')
    }
    result.checks.push(checkLogout)

    if (checkLogout.pass) {
      // Give clearOfflineCaches's async work (awaited by session.ts before the redirect,
      // but the redirect itself tears down the page — read state on the /login page
      // that's already loaded, plus a short grace window for the SW round-trip) a beat.
      await page.waitForTimeout(1000)

      const postLogoutKeyvalKeys = await idbKeyvalKeys(page)
      const postLogoutDraftKeys = await draftStoreKeys(page)
      const postLogoutCaches = await cacheStorageNames(page)
      result.postLogoutKeyvalKeys = postLogoutKeyvalKeys
      result.postLogoutDraftKeys = postLogoutDraftKeys
      result.postLogoutCaches = postLogoutCaches

      result.checks.push({
        name: 'IndexedDB (keyval-store) empty after logout',
        pass: postLogoutKeyvalKeys.length === 0,
        symptom:
          postLogoutKeyvalKeys.length === 0
            ? 'keyval-store fully cleared'
            : `${postLogoutKeyvalKeys.length} key(s) still present after logout: ${JSON.stringify(postLogoutKeyvalKeys.slice(0, 10))}`,
      })

      const leftoverShellOrRuntime = postLogoutCaches.filter(
        (name) => name.includes(':shell') || name.includes(':runtime'),
      )
      const assetCachesRemain = postLogoutCaches.some((name) => name.includes(':assets'))
      result.checks.push({
        name: 'Cache Storage: shell/runtime caches gone, assets cache may remain',
        pass: leftoverShellOrRuntime.length === 0,
        symptom:
          leftoverShellOrRuntime.length === 0
            ? `shell/runtime caches cleared (remaining: ${JSON.stringify(postLogoutCaches)}, assets present=${assetCachesRemain})`
            : `shell/runtime cache(s) still present after logout: ${JSON.stringify(leftoverShellOrRuntime)}`,
      })

      if (draftCreated) {
        result.checks.push({
          name: 'gameplan-drafts NOT cleared on plain logout (Step 0 policy)',
          pass: postLogoutDraftKeys.length > 0,
          symptom:
            postLogoutDraftKeys.length > 0
              ? `${postLogoutDraftKeys.length} draft record(s) survived logout, as intended`
              : 'draft store was wiped on plain logout — Step 0 policy regression (drafts should only clear on a detected user switch)',
        })
      } else {
        result.checks.push({
          name: 'gameplan-drafts NOT cleared on plain logout (Step 0 policy)',
          pass: null,
          symptom: 'skipped — no draft was created pre-logout to check',
        })
      }
    }

    // Overall pass ignores `pass: null` (skipped) checks.
    result.pass = result.checks.every((c) => c.pass !== false)
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    await context.setOffline(false).catch(() => {})
    await browser.close()
  }

  writeResult('us7a', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
