// P1 — Prefetch makes members offline-ready: the background prefetcher
// (frontend/src/data/offlinePrefetch.ts) should warm the People list, every member's
// GP User Profile doc, their bento cards, and their avatar bytes, all without the user
// ever opening the People page or a profile themselves. This story visits ONLY the feed
// online, waits for the prefetcher's '[offline-prefetch] done' log, then goes offline and
// checks: (a) the People page (client-nav + reload) renders member names AND avatars,
// (b) a member's profile NEVER visited in this context renders real content, and
// (c) that member's Posts tab is an honest offline fallback, not a silently-empty list
// (posts are intentionally not prefetched).
const {
  chromium,
  URLS,
  PEOPLE,
  newLoggedInContext,
  waitForPrefetchDone,
  avatarInfo,
  shot,
  innerTextSafe,
  appRootInfo,
  writeResult,
} = require('./helpers')

const MEMBER = PEOPLE.neverVisitedForPrefetch // 'priya-sharma' — never opened in this context

async function warmupFeedOnly(page) {
  await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
  await page.waitForTimeout(1000)
  try {
    await page.evaluate(() => navigator.serviceWorker.ready.then(() => true))
  } catch (e) {
    // best-effort
  }
}

async function fuiSkeletonCount(page) {
  return page.evaluate(() => document.querySelectorAll('.fui-skeleton').length)
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors, prefetchLog } =
    await newLoggedInContext(browser)
  const result = { story: 'P1', checks: [] }

  try {
    await warmupFeedOnly(page)

    // Wait for the idle-delayed background prefetcher to finish its pass. Only the feed
    // was ever visited — People/profiles/bento/avatars must come purely from the
    // prefetcher, not from the user's own browsing.
    const prefetch = await waitForPrefetchDone(prefetchLog, { timeoutMs: 45000 })
    result.prefetch = prefetch
    result.checks.push({
      name: 'prefetch done log observed before going offline',
      pass: prefetch.sawDone && Boolean(prefetch.counts) && prefetch.counts.members > 0,
      symptom: prefetch.sawDone
        ? `saw done line: ${prefetch.doneLine}`
        : `never saw '[offline-prefetch] done' within timeout; log so far: ${JSON.stringify(prefetchLog)}`,
    })

    await context.setOffline(true)

    // (a) People page: client-nav from the feed, then a hard reload, both offline.
    let checkA = { name: 'People page offline: client-nav shows members + avatars' }
    try {
      const peopleRailBtn = page.getByRole('button', { name: 'People', exact: true })
      if (await peopleRailBtn.count()) {
        await peopleRailBtn.click()
      } else {
        await page.goto(URLS.people, { waitUntil: 'load', timeout: 10000 })
      }
      await page.waitForTimeout(2000)

      const text = await innerTextSafe(page)
      const avatars = await avatarInfo(page, 'img')
      const loadedAvatars = avatars.filter((a) => a.naturalWidth > 0)
      const memberishText = /\d+\s+members?/i.test(text) && !/^0\s+members/i.test(text.trim())

      checkA.textSnippet = text.slice(0, 300)
      checkA.avatarCount = avatars.length
      checkA.loadedAvatarCount = loadedAvatars.length
      checkA.screenshot = await shot(page, 'p1-a-clientnav-people')
      checkA.pass = memberishText && loadedAvatars.length > 0
      checkA.symptom = checkA.pass
        ? `member list + ${loadedAvatars.length} loaded avatar(s) rendered from cache`
        : !memberishText
          ? 'no non-zero member count text found (looks like silent-empty or offline fallback)'
          : 'member text present but no avatar image had naturalWidth > 0 (avatars not cached)'
    } catch (e) {
      checkA.pass = false
      checkA.symptom = `threw: ${e.message}`
    }
    result.checks.push(checkA)

    let checkAReload = { name: 'People page offline: hard reload shows members + avatars' }
    try {
      await page.goto(URLS.people, { waitUntil: 'load', timeout: 10000 }).catch((e) => {
        checkAReload.gotoError = String(e)
      })
      await page.waitForTimeout(2000)

      const text = await innerTextSafe(page)
      const avatars = await avatarInfo(page, 'img')
      const loadedAvatars = avatars.filter((a) => a.naturalWidth > 0)
      const memberishText = /\d+\s+members?/i.test(text) && !/^0\s+members/i.test(text.trim())

      checkAReload.textSnippet = text.slice(0, 300)
      checkAReload.avatarCount = avatars.length
      checkAReload.loadedAvatarCount = loadedAvatars.length
      checkAReload.screenshot = await shot(page, 'p1-a-reload-people')
      checkAReload.pass = memberishText && loadedAvatars.length > 0
      checkAReload.symptom = checkAReload.pass
        ? `member list + ${loadedAvatars.length} loaded avatar(s) rendered from cache after hard reload`
        : !memberishText
          ? 'no non-zero member count text found after reload'
          : 'member text present but no avatar image had naturalWidth > 0 after reload'
    } catch (e) {
      checkAReload.pass = false
      checkAReload.symptom = `threw: ${e.message}`
    }
    result.checks.push(checkAReload)

    // (b) A member's profile never visited in this context — should render real content
    // from the profile doc + bento cache the prefetcher warmed, not a skeleton forever and
    // not a false NotFound.
    let checkB = { name: `never-visited profile (${MEMBER}) renders offline` }
    try {
      await page.goto(URLS.person(MEMBER), { waitUntil: 'load', timeout: 10000 }).catch((e) => {
        checkB.gotoError = String(e)
      })
      await page.waitForTimeout(2500)

      const skeletonBefore = await fuiSkeletonCount(page)
      await page.waitForTimeout(3000)
      const skeletonAfter = await fuiSkeletonCount(page)
      const stuckOnSkeleton = skeletonBefore > 0 && skeletonAfter > 0

      const text = await innerTextSafe(page)
      const info = await appRootInfo(page)
      const isNotFound = /page not found/i.test(text)
      const hasCardContent = await page
        .locator('[data-profile-card-wrapper="true"], [data-profile-empty-state]')
        .count()

      checkB.textSnippet = text.slice(0, 400)
      checkB.stuckOnSkeleton = stuckOnSkeleton
      checkB.isNotFound = isNotFound
      checkB.hasCardContent = hasCardContent > 0
      checkB.info = info
      checkB.screenshot = await shot(page, 'p1-b-unvisited-profile')
      checkB.pass = !stuckOnSkeleton && !isNotFound && hasCardContent > 0
      checkB.symptom = checkB.pass
        ? 'profile header + bento content rendered from prefetched cache'
        : stuckOnSkeleton
          ? 'stuck on skeleton — bento cards never resolved'
          : isNotFound
            ? 'showed NotFound instead of prefetched profile content'
            : 'neither bento cards nor empty-state box rendered (blank content area)'
    } catch (e) {
      checkB.pass = false
      checkB.symptom = `threw: ${e.message}`
      checkB.screenshot = await shot(page, 'p1-b-unvisited-profile-error')
    }
    result.checks.push(checkB)

    // (c) That member's Posts tab — posts are NOT prefetched, so this must be the honest
    // offline fallback (OfflineContentFallback), never a silently-empty "no posts" list.
    let checkC = { name: `never-visited profile (${MEMBER}) Posts tab: honest offline fallback` }
    try {
      const postsTabBtn = page.locator('button', { hasText: 'Posts' }).first()
      if (await postsTabBtn.count()) {
        await postsTabBtn.click()
        await page.waitForTimeout(2000)
      } else {
        await page.goto(URLS.personPosts(MEMBER), { waitUntil: 'load', timeout: 10000 })
        await page.waitForTimeout(2000)
      }

      const text = await innerTextSafe(page)
      const fallbackDetected =
        /can.?t load this while offline|haven.?t been saved for offline use/i.test(text)
      const retryVisible = await page.locator('button:has-text("Retry")').count()

      checkC.textSnippet = text.slice(0, 400)
      checkC.fallbackDetected = fallbackDetected
      checkC.retryVisible = retryVisible > 0
      checkC.screenshot = await shot(page, 'p1-c-unvisited-posts-tab')
      checkC.pass = fallbackDetected && retryVisible > 0
      checkC.symptom = checkC.pass
        ? 'honest offline fallback with retry shown for un-prefetched posts'
        : 'no offline-fallback messaging/retry found — risk of silently-empty posts list'
    } catch (e) {
      checkC.pass = false
      checkC.symptom = `threw: ${e.message}`
      checkC.screenshot = await shot(page, 'p1-c-unvisited-posts-tab-error')
    }
    result.checks.push(checkC)

    result.pass = result.checks.every((c) => c.pass)
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    result.prefetchLog = prefetchLog
    await context.setOffline(false).catch(() => {})
    await browser.close()
  }

  writeResult('p1', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
