// P3 — Honest failure without cache: a session that goes offline before the background
// prefetcher (data/offlinePrefetch.ts) or any manual browsing populated the People/profile
// caches must show an honest "can't load this offline" fallback with retry — never a
// silent "0 members" empty list, an infinite skeleton, or a misleading NotFound.
//
// Race note: we go offline as fast as possible after the very first (minimal) online page
// load, before the prefetcher's idle-delayed pass can finish. If the prefetcher still wins
// the race in a given run (slow/fast CI hardware makes the exact timing non-deterministic),
// we fall back to explicitly deleting the specific IndexedDB cache entries the prefetcher
// would have written (People list, this profile's doc, this profile's bento) — the
// documented escape hatch in the task brief — so the "no cache" condition this story is
// actually about is guaranteed either way, and which path was taken is recorded in the
// result for transparency.
const {
  chromium,
  URLS,
  PEOPLE,
  EMAIL,
  newLoggedInContext,
  shot,
  innerTextSafe,
  appRootInfo,
  writeResult,
} = require('./helpers')

const MEMBER = PEOPLE.neverVisitedNoPrefetch // 'hana-suzuki'

// Mirrors frappe-ui's idb-keyval default store (idbStore.ts -> createStore('keyval-store',
// 'keyval')) and the exact key shapes data/people.ts, ProfileBento/profileBentoSource.ts,
// and docStore.ts write to, so this only ever touches the People/this-profile entries — not
// session/communities/spaces data the app needs to know it's still logged in offline.
async function clearPeopleAndProfileCache(page, personId, sessionUser) {
  const keysToDelete = [
    JSON.stringify(['useList', 'People', sessionUser]),
    JSON.stringify(['useCall', 'ProfileBento', personId, sessionUser]),
    `doc:GP User Profile/${personId}`,
  ]
  return page.evaluate((keys) => {
    return new Promise((resolve) => {
      const req = indexedDB.open('keyval-store')
      req.onsuccess = () => {
        const db = req.result
        if (!db.objectStoreNames.contains('keyval')) {
          db.close()
          resolve({ deleted: [], reason: 'no keyval store' })
          return
        }
        const tx = db.transaction('keyval', 'readwrite')
        const store = tx.objectStore('keyval')
        keys.forEach((k) => store.delete(k))
        tx.oncomplete = () => {
          db.close()
          resolve({ deleted: keys })
        }
        tx.onerror = () => {
          db.close()
          resolve({ deleted: [], reason: String(tx.error) })
        }
      }
      req.onerror = () => resolve({ deleted: [], reason: String(req.error) })
    })
  }, keysToDelete)
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors, prefetchLog } =
    await newLoggedInContext(browser)
  const result = { story: 'P3', checks: [] }

  try {
    // Minimal online exposure: enough for the SW to register and become active (it only
    // starts registering on the window `load` event - see offline.ts's setupOfflineSupport
    // - and a subsequent offline navigation needs it active to serve the shell at all,
    // which is a US1 concern, not what this story is testing) but deliberately not waiting
    // for anything past that, so we go offline as close as possible to page load, ahead of
    // the prefetcher's idle-delayed kickoff.
    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
    // `/g` itself client-side redirects to the community's discussions route once the
    // app has hydrated enough to know where to send you (post-327d7ae3, cache-hydration
    // gated, so not always instant). This story doesn't actually depend on racing ahead
    // of that specific redirect — only ahead of the background prefetcher's much slower
    // idle-delayed pass, and it force-clears the People/profile/bento cache entries
    // below regardless of how any race went (see the comment above) — so it's safe to
    // let the redirect land first, rather than risk it firing mid-`page.evaluate()`
    // below and destroying the execution context out from under this test.
    await page.waitForURL(/\/g\/community\//, { timeout: 10000 }).catch(() => {})
    try {
      await page.evaluate(() => navigator.serviceWorker.ready.then(() => true))
    } catch (e) {
      // best-effort - if this never resolves, the offline navigations below will
      // surface it as a shell-level failure rather than the data-layer fallback.
    }
    await context.setOffline(true)

    const sawDoneBeforeOffline = prefetchLog.some((l) => l.includes('[offline-prefetch] done'))
    result.racedSuccessfully = !sawDoneBeforeOffline
    result.prefetchLogAtOfflineTime = [...prefetchLog]

    // Always clear, not just when the prefetcher's "done" log won the race: `data/people.ts`
    // exports its `people` list as a module-level `useList({ immediate: true })` singleton,
    // so the People list starts fetching the moment the app boots on ANY page (imported
    // transitively by main.js -> offlinePrefetch.ts -> people.ts) - well before the
    // prefetcher's own idle-delayed pass, and far faster than this script can react after
    // the page `load` event. Racing `setOffline` against that fetch is not reliably
    // winnable, so - per the task brief's documented escape hatch - this story always forces
    // the "nothing cached yet" condition it's actually about, rather than depending on
    // timing luck for a signal (`people.ts`'s own immediate fetch) this story never races on.
    result.cacheClear = await clearPeopleAndProfileCache(page, MEMBER, EMAIL)

    result.checks.push({
      name: 'no People/profile/bento cache present before navigating offline',
      pass: Boolean(result.cacheClear && result.cacheClear.deleted?.length),
      symptom: sawDoneBeforeOffline
        ? `prefetch "done" log had already fired; cleared its cache entries: ${JSON.stringify(result.cacheClear)}`
        : `raced offline ahead of prefetch "done"; cleared cache entries anyway (people.ts's own immediate fetch races independently): ${JSON.stringify(result.cacheClear)}`,
    })

    // People page: must show an offline fallback with retry, not "0 members".
    let checkPeople = { name: 'People page offline, no cache: honest fallback with retry' }
    try {
      await page.goto(URLS.people, { waitUntil: 'load', timeout: 10000 }).catch((e) => {
        checkPeople.gotoError = String(e)
      })
      await page.waitForTimeout(2000)

      const text = await innerTextSafe(page)
      const info = await appRootInfo(page)
      const fallbackDetected = /can.?t load|not available while offline|offline/i.test(text)
      const retryVisible = await page.locator('button:has-text("Retry")').count()
      // "0 members" in the header count is fine as long as it's paired with the honest
      // fallback message below it — that's a live count reading zero because `people.data`
      // is null, not a silent claim that the org has no members. Only flag it when there's
      // no fallback messaging to explain the zero (the actual US6-class bug this guards).
      const silentEmpty = !fallbackDetected && /\b0 members\b/i.test(text)

      checkPeople.textSnippet = text.slice(0, 400)
      checkPeople.info = info
      checkPeople.silentEmpty = silentEmpty
      checkPeople.fallbackDetected = fallbackDetected
      checkPeople.retryVisible = retryVisible > 0
      checkPeople.screenshot = await shot(page, 'p3-people-no-cache')
      checkPeople.pass = !silentEmpty && fallbackDetected && retryVisible > 0
      checkPeople.symptom = checkPeople.pass
        ? 'honest offline fallback with retry shown (not silent "0 members")'
        : silentEmpty
          ? 'silent "0 members" with no fallback messaging — indistinguishable from an empty org (US6-class bug)'
          : !fallbackDetected
            ? 'no offline messaging found'
            : 'no retry affordance found'
    } catch (e) {
      checkPeople.pass = false
      checkPeople.symptom = `threw: ${e.message}`
      checkPeople.screenshot = await shot(page, 'p3-people-no-cache-error')
    }
    result.checks.push(checkPeople)

    // A profile with nothing cached: honest fallback, not infinite skeleton, not a
    // misleading "page not found".
    let checkProfile = { name: `profile (${MEMBER}) offline, no cache: honest fallback` }
    try {
      await page.goto(URLS.person(MEMBER), { waitUntil: 'load', timeout: 10000 }).catch((e) => {
        checkProfile.gotoError = String(e)
      })
      await page.waitForTimeout(2000)
      const skeletonBefore = await page.evaluate(
        () => document.querySelectorAll('.fui-skeleton').length,
      )
      await page.waitForTimeout(3000)
      const skeletonAfter = await page.evaluate(
        () => document.querySelectorAll('.fui-skeleton').length,
      )
      const stuckOnSkeleton = skeletonBefore > 0 && skeletonAfter > 0

      const text = await innerTextSafe(page)
      const isNotFound = /page not found/i.test(text)
      const fallbackDetected =
        /can.?t load this (profile )?while offline|isn.?t available offline/i.test(text)
      const retryVisible = await page.locator('button:has-text("Retry")').count()

      checkProfile.textSnippet = text.slice(0, 400)
      checkProfile.stuckOnSkeleton = stuckOnSkeleton
      checkProfile.isNotFound = isNotFound
      checkProfile.fallbackDetected = fallbackDetected
      checkProfile.retryVisible = retryVisible > 0
      checkProfile.screenshot = await shot(page, 'p3-profile-no-cache')
      checkProfile.pass = !stuckOnSkeleton && !isNotFound && fallbackDetected
      checkProfile.symptom = checkProfile.pass
        ? 'honest "can\'t load this profile while offline" fallback shown'
        : stuckOnSkeleton
          ? 'stuck on skeleton forever'
          : isNotFound
            ? 'misleading NotFound page shown instead of an offline fallback'
            : 'no offline fallback messaging detected'
    } catch (e) {
      checkProfile.pass = false
      checkProfile.symptom = `threw: ${e.message}`
      checkProfile.screenshot = await shot(page, 'p3-profile-no-cache-error')
    }
    result.checks.push(checkProfile)

    result.pass = result.checks.every((c) => c.pass)
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    await context.setOffline(false).catch(() => {})
    await browser.close()
  }

  writeResult('p3', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
