// US7c — Shared-computer safety, abandoned-session path: A's session becomes invalid
// without an explicit logout (timeout, stale tab, bookmark), the SPA boots as Guest on
// the next /g load, and a second person logs in right after. Must clear A's offline
// content exactly like US7b's switch does.
//
// Doesn't use logoutViaUI/session.logout — that calls clearOfflineCaches() directly and
// would mask this bug. Instead drops cookies the way an actually-expired session presents
// to the SPA (frappe/sessions.py clears user_id/sid server-side before the SPA's JS runs;
// gameplan/www/g.py's require_app_access lets Guest boot the SPA shell rather than 403ing).
const {
  chromium,
  URLS,
  BASE,
  PEOPLE,
  EMAIL,
  EMAIL2,
  PWD2,
  newLoggedInContext,
  loginAsInSameContext,
  idbKeyvalKeys,
  lastSeenUserFromStorage,
  innerTextSafe,
  shot,
  writeResult,
} = require('./helpers')

const MEMBER = PEOPLE.visitedFully // 'maya-iyer'

// A space+discussion only A is a member of (seeded separately from config.js's shared
// content — see gameplan/debug.py's one-off seed). Its content is fetched via useDoc
// (data/discussions.ts), which has no cacheKey/user-scoping at all (unlike the useList
// caches checked by key prefix below), so B genuinely has no access to it — a rendered
// leak here can't be explained away as B's own legitimate re-fetch.
const PRIVATE_DISCUSSION_URL = `${BASE}/g/community/common-room/space/1426/discussion/722/us7c-secret-discussion`
const PRIVATE_MARKER = 'us7c-secret-marker-do-not-leak'

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US7c', checks: [] }

  try {
    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
    await page.waitForURL(/\/g\/community\//, { timeout: 10000 }).catch(() => {})
    await page.waitForTimeout(1000)
    await page.goto(URLS.people, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1000)
    await page.goto(URLS.person(MEMBER), { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1500)
    await page.goto(PRIVATE_DISCUSSION_URL, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1500)
    try {
      await page.evaluate(() => navigator.serviceWorker.ready.then(() => true))
    } catch (e) {
      // best-effort
    }

    const userAKeyvalKeys = await idbKeyvalKeys(page)
    const userALastSeen = await lastSeenUserFromStorage(page)
    result.userAKeyvalCount = userAKeyvalKeys.length
    result.userALastSeen = userALastSeen

    result.checks.push({
      name: 'user A caches populated, last-seen-user recorded as A',
      pass: userAKeyvalKeys.length > 0 && userALastSeen === EMAIL,
      symptom: `keyvalKeys=${userAKeyvalKeys.length} lastSeen=${userALastSeen}`,
    })

    // A's session ends without an explicit logout.
    await context.clearCookies()

    // Boot the SPA as Guest — the only place guardAgainstUserSwitch(null) runs here.
    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 }).catch(() => {})
    await page.waitForTimeout(1000)

    const lastSeenAfterGuestBoot = await lastSeenUserFromStorage(page)
    result.lastSeenAfterGuestBoot = lastSeenAfterGuestBoot

    result.checks.push({
      name: "last-seen-user marker survives a logged-out /g boot (still says A, isn't erased)",
      pass: lastSeenAfterGuestBoot === EMAIL,
      symptom:
        lastSeenAfterGuestBoot === EMAIL
          ? 'marker still identifies A after the guest boot, as intended'
          : `marker was erased/changed by the logged-out boot (now ${JSON.stringify(
              lastSeenAfterGuestBoot,
            )}) - the next real login won't be recognized as a switch, so A's caches never get cleared`,
    })

    await loginAsInSameContext(context, page, EMAIL2, PWD2)
    await page.waitForTimeout(1500)

    const userBLastSeen = await lastSeenUserFromStorage(page)
    const postSwitchKeyvalKeys = await idbKeyvalKeys(page)
    const leakedAKeys = postSwitchKeyvalKeys.filter((k) => k.includes(EMAIL))
    result.userBLastSeen = userBLastSeen
    result.postSwitchKeyvalKeys = postSwitchKeyvalKeys
    result.leakedAKeys = leakedAKeys

    result.checks.push({
      name: 'localStorage last-seen-user updated to B after the switch is detected',
      pass: userBLastSeen === EMAIL2,
      symptom: `lastSeen=${userBLastSeen} (expected ${EMAIL2})`,
    })

    result.checks.push({
      name: "user-switch clear ran: no useList-cached key tagged with A's identity survives",
      pass: leakedAKeys.length === 0,
      symptom:
        leakedAKeys.length === 0
          ? `A's keys cleared on the detected switch (${
              postSwitchKeyvalKeys.length
            } key(s) remain, all B's own: ${JSON.stringify(postSwitchKeyvalKeys)})`
          : `${
              leakedAKeys.length
            } key(s) still tagged with A's identity after the switch: ${JSON.stringify(
              leakedAKeys,
            )}`,
    })

    // docStore keys carry no per-user identity at all (doc:<doctype>/<name> only), so the
    // filter above can't catch this leak — check the private discussion's key directly.
    const privateDiscussionKeySurvived = postSwitchKeyvalKeys.includes('doc:GP Discussion/722')
    result.checks.push({
      name: "user-switch clear ran: A's private discussion doc is gone from IndexedDB",
      pass: !privateDiscussionKeySurvived,
      symptom: privateDiscussionKeySurvived
        ? "doc:GP Discussion/722 (A's, content B has no access to) is still in IndexedDB after the switch"
        : 'doc:GP Discussion/722 cleared on the detected switch',
    })

    await context.setOffline(true)

    let checkPeople = { name: "People page offline as B: does not show A's cached member list" }
    try {
      await page.goto(URLS.people, { waitUntil: 'load', timeout: 10000 }).catch((e) => {
        checkPeople.gotoError = String(e)
      })
      await page.waitForTimeout(2000)
      const text = await innerTextSafe(page)
      const honestFallback = /can.?t load|not available while offline|offline/i.test(text)
      const rendersMemberList = /\d+\s+members?/i.test(text) && !/^0\s+members/i.test(text.trim())
      const leaked = rendersMemberList && !honestFallback

      checkPeople.textSnippet = text.slice(0, 400)
      checkPeople.honestFallback = honestFallback
      checkPeople.rendersMemberList = rendersMemberList
      checkPeople.screenshot = await shot(page, 'us7c-people-offline-userB')
      checkPeople.pass = !leaked
      checkPeople.symptom = checkPeople.pass
        ? honestFallback
          ? 'honest offline fallback shown (no leaked member list)'
          : 'no member list rendered (empty/loading state, not a leak)'
        : "user A's cached member list rendered for user B offline — cross-user cache leak"
    } catch (e) {
      checkPeople.pass = false
      checkPeople.symptom = `threw: ${e.message}`
      checkPeople.screenshot = await shot(page, 'us7c-people-offline-userB-error')
    }
    result.checks.push(checkPeople)

    let checkPrivate = {
      name: 'private discussion offline as B: rendered UI does not show it either',
    }
    try {
      await page.goto(PRIVATE_DISCUSSION_URL, { waitUntil: 'load', timeout: 10000 }).catch((e) => {
        checkPrivate.gotoError = String(e)
      })
      await page.waitForTimeout(2500)
      const text = await innerTextSafe(page)
      const leaked = text.includes(PRIVATE_MARKER)

      checkPrivate.textSnippet = text.slice(0, 400)
      checkPrivate.screenshot = await shot(page, 'us7c-private-discussion-offline-userB')
      checkPrivate.pass = !leaked
      checkPrivate.symptom = checkPrivate.pass
        ? 'content not accessible to B (not-found/empty/offline fallback — B was never a member of this space)'
        : "A's private discussion content rendered for user B offline — cross-user docStore cache leak"
    } catch (e) {
      checkPrivate.pass = false
      checkPrivate.symptom = `threw: ${e.message}`
      checkPrivate.screenshot = await shot(page, 'us7c-private-discussion-offline-userB-error')
    }
    result.checks.push(checkPrivate)

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

  writeResult('us7c', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
