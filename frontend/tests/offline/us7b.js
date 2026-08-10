// US7b — Shared-computer safety, user-switch path: a SECOND person logging in on the
// same browser right after the first must not be able to read anything the first user's
// session left behind. Continues in the SAME browser context as a fresh login (not a new
// context) — that's what actually exercises guardAgainstUserSwitch (frontend/src/offline.ts),
// which compares the incoming user_id cookie against localStorage's
// 'gameplan:last-seen-user' and clears every offline cache (+ drafts — see US7a's Step 0
// note) the moment it detects a mismatch.
const {
  chromium,
  URLS,
  PEOPLE,
  EMAIL,
  EMAIL2,
  PWD2,
  newLoggedInContext,
  loginAsInSameContext,
  waitForPrefetchDone,
  idbKeyvalKeys,
  draftStoreKeys,
  lastSeenUserFromStorage,
  innerTextSafe,
  shot,
  writeResult,
} = require('./helpers')

// A profile user A visited and cached; used to check user B can't read it offline.
const MEMBER = PEOPLE.visitedFully // 'maya-iyer'

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors, prefetchLog } =
    await newLoggedInContext(browser)
  const result = { story: 'US7b', checks: [] }

  try {
    // --- User A: warm real caches, including the People page and MEMBER's profile. ---
    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
    // See us7a.js/loginAsInSameContext's identical comment: let /g's client-side
    // redirect to the community's discussions route land before the next goto(), or it
    // can get reported as "interrupted by another navigation".
    await page.waitForURL(/\/g\/community\//, { timeout: 10000 }).catch(() => {})
    await page.waitForTimeout(1000)
    await page.goto(URLS.people, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1000)
    await page.goto(URLS.person(MEMBER), { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1500)
    try {
      await page.evaluate(() => navigator.serviceWorker.ready.then(() => true))
    } catch (e) {
      // best-effort
    }
    await waitForPrefetchDone(prefetchLog, { timeoutMs: 20000 }) // best-effort, not required to pass

    const userAKeyvalKeys = await idbKeyvalKeys(page)
    const userALastSeen = await lastSeenUserFromStorage(page)
    result.userAKeyvalCount = userAKeyvalKeys.length
    result.userALastSeen = userALastSeen

    result.checks.push({
      name: 'user A caches populated, last-seen-user recorded as A',
      pass: userAKeyvalKeys.length > 0 && userALastSeen === EMAIL,
      symptom: `keyvalKeys=${userAKeyvalKeys.length} lastSeen=${userALastSeen}`,
    })

    // --- Switch: log in as user B in the SAME browser context, no explicit logout first
    // (worst case for a shared computer — someone just switches accounts). guardAgainstUserSwitch
    // runs at module boot on the next navigation, so loginAsInSameContext already does the
    // follow-up page.goto(feed) that triggers it. ---
    await loginAsInSameContext(context, page, EMAIL2, PWD2)
    await page.waitForTimeout(1500) // let the async clearOfflineCaches()/clearDraftStore() settle

    const userBLastSeen = await lastSeenUserFromStorage(page)
    const postSwitchKeyvalKeys = await idbKeyvalKeys(page)
    // Any key still containing A's identity is the actual leak signal. Keys stamped with
    // B's own identity are expected here — the app's own useCall/useList singletons start
    // re-fetching for B the instant the post-switch reload boots, racing (and normally
    // winning shortly after) the async clear, and correctly write back under B's own
    // cacheKey. That's not a leak; it's B's data, scoped to B.
    const leakedAKeys = postSwitchKeyvalKeys.filter((k) => k.includes(EMAIL))
    result.userBLastSeen = userBLastSeen
    result.postSwitchKeyvalKeys = postSwitchKeyvalKeys
    result.leakedAKeys = leakedAKeys

    result.checks.push({
      name: 'localStorage last-seen-user updated to B after switch',
      pass: userBLastSeen === EMAIL2,
      symptom: `lastSeen=${userBLastSeen} (expected ${EMAIL2})`,
    })

    result.checks.push({
      name: "user-switch clear ran: no key tagged with A's identity survives the switch",
      pass: leakedAKeys.length === 0,
      symptom:
        leakedAKeys.length === 0
          ? `A's keys cleared on detected user switch (${postSwitchKeyvalKeys.length} key(s) remain, all B's own: ${JSON.stringify(postSwitchKeyvalKeys)})`
          : `${leakedAKeys.length} key(s) still tagged with A's identity after switch: ${JSON.stringify(leakedAKeys)}`,
    })

    // Diagnostic only (not gating US7b's pass/fail, which is about cross-user leakage,
    // not general offline-shell availability — see the note below and results-round4.md):
    // CLEAR_USER_CACHES also deletes SHELL_CACHE (gameplan-sw.js's clearUserCaches), and
    // nothing repopulates it until the NEXT successful online navigation. The online
    // reload above that triggered this switch detection did write a fresh shell via
    // networkFirstNavigation - but the switch-clear (fired from this same page's JS,
    // shortly after) deletes it again moments later, with no further online navigation
    // in between. Verified independently (ad hoc script) that this leaves the browser
    // with an empty SHELL_CACHE indefinitely - even a plain reload of /g itself then
    // fails with net::ERR_FAILED while offline, not the app's own offline UI. This is a
    // real app-side gap (not present before this round's user-switch clearing feature),
    // not typo-level, so it is reported here as evidence rather than fixed.
    const postSwitchCaches = await page.evaluate(() => caches.keys())
    result.postSwitchCaches = postSwitchCaches
    result.checks.push({
      name: '[diagnostic, non-gating] SHELL_CACHE survives the user-switch clear',
      pass: null,
      symptom: postSwitchCaches.some((n) => n.includes(':shell'))
        ? 'shell cache present after switch'
        : `SHELL_CACHE absent after switch clear (caches now: ${JSON.stringify(postSwitchCaches)}) - a reload while offline from here fails with net::ERR_FAILED instead of the app's offline UI; see results-round4.md`,
    })

    // --- Now go offline immediately, before B's own prefetch/browsing could plausibly
    // have cached anything of A's, and check B truly can't see A's content. ---
    await context.setOffline(true)

    let checkPeople = { name: "People page offline as B: does not show A's cached member list" }
    try {
      await page.goto(URLS.people, { waitUntil: 'load', timeout: 10000 }).catch((e) => {
        checkPeople.gotoError = String(e)
      })
      await page.waitForTimeout(2000)
      const text = await innerTextSafe(page)
      const honestFallback = /can.?t load|not available while offline|offline/i.test(text)
      // The only way this could wrongly "succeed" is if A's member list actually rendered
      // (a real leak) — a large member count with no fallback messaging is the signature.
      const rendersMemberList = /\d+\s+members?/i.test(text) && !/^0\s+members/i.test(text.trim())
      const leaked = rendersMemberList && !honestFallback

      checkPeople.textSnippet = text.slice(0, 400)
      checkPeople.honestFallback = honestFallback
      checkPeople.rendersMemberList = rendersMemberList
      checkPeople.screenshot = await shot(page, 'us7b-people-offline-userB')
      checkPeople.pass = !leaked
      checkPeople.symptom = checkPeople.pass
        ? honestFallback
          ? 'honest offline fallback shown (no leaked member list)'
          : 'no member list rendered (empty/loading state, not a leak)'
        : "user A's cached member list rendered for user B offline — cross-user cache leak"
    } catch (e) {
      checkPeople.pass = false
      checkPeople.symptom = `threw: ${e.message}`
      checkPeople.screenshot = await shot(page, 'us7b-people-offline-userB-error')
    }
    result.checks.push(checkPeople)

    let checkProfile = {
      name: `profile (${MEMBER}) offline as B: does not show A's cached profile`,
    }
    try {
      await page.goto(URLS.person(MEMBER), { waitUntil: 'load', timeout: 10000 }).catch((e) => {
        checkProfile.gotoError = String(e)
      })
      await page.waitForTimeout(2500)
      const text = await innerTextSafe(page)
      const isNotFound = /page not found/i.test(text)
      const honestFallback =
        /can.?t load this (profile )?while offline|isn.?t available offline/i.test(text)
      const hasCardContent = await page.locator('[data-profile-card-wrapper="true"]').count()
      // Real leak signature: A's bento/profile card content actually rendered for B.
      const leaked = hasCardContent > 0 && !honestFallback

      checkProfile.textSnippet = text.slice(0, 400)
      checkProfile.isNotFound = isNotFound
      checkProfile.honestFallback = honestFallback
      checkProfile.hasCardContent = hasCardContent > 0
      checkProfile.screenshot = await shot(page, 'us7b-profile-offline-userB')
      // Honest fallback, an empty/not-found state, or a stuck skeleton are all acceptable
      // ("honest fallback/empty is correct" per the task brief) — only a rendered card with
      // A's content and no fallback messaging is a fail.
      checkProfile.pass = !leaked
      checkProfile.symptom = checkProfile.pass
        ? honestFallback
          ? 'honest "can\'t load this profile while offline" fallback shown'
          : 'no profile content rendered for B (not-found/empty/skeleton — not a leak)'
        : "user A's cached profile content rendered for user B offline — cross-user cache leak"
    } catch (e) {
      checkProfile.pass = false
      checkProfile.symptom = `threw: ${e.message}`
      checkProfile.screenshot = await shot(page, 'us7b-profile-offline-userB-error')
    }
    result.checks.push(checkProfile)

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

  writeResult('us7b', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
