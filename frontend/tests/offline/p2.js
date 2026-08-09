// P2 — A profile visited fully online (header + bento + Posts) should work fully offline
// on reload: header, bento cards, and posts all rendering from cache — no reliance on the
// background prefetcher (which never warms posts) because this session visited everything
// itself.
const {
  chromium,
  URLS,
  PEOPLE,
  newLoggedInContext,
  avatarInfo,
  shot,
  innerTextSafe,
  appRootInfo,
  writeResult,
} = require('./helpers')

const MEMBER = PEOPLE.visitedFully // 'maya-iyer' — has real posts (see env notes)

async function fuiSkeletonCount(page) {
  return page.evaluate(() => document.querySelectorAll('.fui-skeleton').length)
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'P2', checks: [] }

  try {
    // Online warmup: visit the profile (header + bento) and its Posts tab, and let the
    // service worker finish caching (mirrors helpers.warmup's SW-ready wait).
    await page.goto(URLS.person(MEMBER), { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(2000)
    const postsTabBtn = page.locator('button', { hasText: 'Posts' }).first()
    if (await postsTabBtn.count()) {
      await postsTabBtn.click()
      await page.waitForTimeout(2000)
    }
    try {
      await page.evaluate(() => navigator.serviceWorker.ready.then(() => true))
    } catch (e) {
      // best-effort
    }
    await page.waitForTimeout(4000) // warmLoadedAssets() follow-up timer

    result.onlineWarmupUrl = page.url()

    await context.setOffline(true)

    // Hard reload straight onto the Posts tab URL — the harder case, since it must
    // hydrate the profile header (parent route) and the posts list (child route) from
    // cache in one navigation.
    let checkPosts = { name: 'reload on Posts tab: header + posts render offline' }
    try {
      await page
        .goto(URLS.personPosts(MEMBER), { waitUntil: 'load', timeout: 10000 })
        .catch((e) => {
          checkPosts.gotoError = String(e)
        })
      await page.waitForTimeout(2500)

      const text = await innerTextSafe(page)
      const info = await appRootInfo(page)
      const postLinks = await page.locator('a[href*="/discussion/"]').count()
      const isNotFound = /page not found/i.test(text)
      const fallbackShown =
        /can.?t load this while offline|haven.?t been saved for offline use/i.test(text)

      checkPosts.textSnippet = text.slice(0, 400)
      checkPosts.info = info
      checkPosts.postLinks = postLinks
      checkPosts.isNotFound = isNotFound
      checkPosts.fallbackShown = fallbackShown
      checkPosts.screenshot = await shot(page, 'p2-reload-posts-tab')
      checkPosts.pass = !isNotFound && !fallbackShown && postLinks > 0
      checkPosts.symptom = checkPosts.pass
        ? `${postLinks} cached post row(s) rendered offline`
        : isNotFound
          ? 'NotFound shown instead of cached profile'
          : fallbackShown
            ? 'offline fallback shown even though Posts tab was visited online first (cache miss)'
            : 'no post rows found — posts list likely empty/blank'
    } catch (e) {
      checkPosts.pass = false
      checkPosts.symptom = `threw: ${e.message}`
      checkPosts.screenshot = await shot(page, 'p2-reload-posts-tab-error')
    }
    result.checks.push(checkPosts)

    // Now reload onto the Profile tab specifically, to check header + bento independent
    // of whatever the Posts-tab reload left mounted.
    let checkProfile = { name: 'reload on Profile tab: header + bento render offline' }
    try {
      await page.goto(URLS.person(MEMBER), { waitUntil: 'load', timeout: 10000 }).catch((e) => {
        checkProfile.gotoError = String(e)
      })
      await page.waitForTimeout(2500)

      const skeletonBefore = await fuiSkeletonCount(page)
      await page.waitForTimeout(3000)
      const skeletonAfter = await fuiSkeletonCount(page)
      const stuckOnSkeleton = skeletonBefore > 0 && skeletonAfter > 0

      const text = await innerTextSafe(page)
      const isNotFound = /page not found/i.test(text)
      const hasCardContent = await page
        .locator('[data-profile-card-wrapper="true"], [data-profile-empty-state]')
        .count()
      const avatars = await avatarInfo(page, 'img')
      const loadedAvatars = avatars.filter((a) => a.naturalWidth > 0)

      checkProfile.textSnippet = text.slice(0, 400)
      checkProfile.stuckOnSkeleton = stuckOnSkeleton
      checkProfile.isNotFound = isNotFound
      checkProfile.hasCardContent = hasCardContent > 0
      checkProfile.loadedAvatarCount = loadedAvatars.length
      checkProfile.screenshot = await shot(page, 'p2-reload-profile-tab')
      checkProfile.pass = !stuckOnSkeleton && !isNotFound && hasCardContent > 0
      checkProfile.symptom = checkProfile.pass
        ? 'header + bento content rendered from cache on reload'
        : stuckOnSkeleton
          ? 'stuck on skeleton — bento cards never resolved offline'
          : isNotFound
            ? 'showed NotFound instead of cached profile'
            : 'neither bento cards nor empty-state box rendered'
    } catch (e) {
      checkProfile.pass = false
      checkProfile.symptom = `threw: ${e.message}`
      checkProfile.screenshot = await shot(page, 'p2-reload-profile-tab-error')
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

  writeResult('p2', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
