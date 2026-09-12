// Online regression smoke test (round 3 addition) — fresh context, always online. Confirms
// the People page and a member profile load normally with the new caching/prefetch code in
// place, no new console errors beyond the known :9000 socket.io refusal (see env.md), and
// the background prefetcher's '[offline-prefetch] done' log appears with plausible counts.
// Complements smoke-online.js (feed/space/discussion + comment post/delete), which this
// does not repeat.
const {
  chromium,
  URLS,
  PEOPLE,
  newLoggedInContext,
  waitForPrefetchDone,
  avatarInfo,
  shot,
  innerTextSafe,
  writeResult,
} = require('./helpers')

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors, prefetchLog } =
    await newLoggedInContext(browser)
  const result = { story: 'SMOKE-ONLINE-PEOPLE', checks: [] }

  // `msg.text()` for a "Failed to load resource" console error doesn't include the URL, so
  // matching it against a socket.io/:9000 regex (as smoke-online.js's own comment describes
  // doing "via a requestfailed listener") needs the request-level event instead - track how
  // many of those failures are the known :9000 socket.io refusal so the console-error check
  // below can subtract exactly that many, not just pattern-match on generic text.
  let socketIoFailures = 0
  page.on('requestfailed', (req) => {
    if (/:9000\/socket\.io/i.test(req.url())) socketIoFailures++
  })

  try {
    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
    // See smoke-online.js's identical comment: let /g's client-side redirect land first.
    await page.waitForURL(/\/g\/community\//, { timeout: 10000 }).catch(() => {})
    await page.waitForTimeout(1000)

    // People page
    let checkPeople = { name: 'People page loads online' }
    await page.goto(URLS.people, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1500)
    const peopleText = await innerTextSafe(page)
    const avatars = await avatarInfo(page, 'img')
    const loadedAvatars = avatars.filter((a) => a.naturalWidth > 0)
    checkPeople.textSnippet = peopleText.slice(0, 300)
    checkPeople.loadedAvatarCount = loadedAvatars.length
    checkPeople.pass =
      /\d+\s+members?/i.test(peopleText) && !/^0\s+members/i.test(peopleText.trim())
    checkPeople.symptom = checkPeople.pass
      ? 'member list rendered online'
      : 'People page did not render a real member count online'
    checkPeople.screenshot = await shot(page, 'smoke-people-online')
    result.checks.push(checkPeople)

    // A profile
    let checkProfile = { name: 'A member profile loads online' }
    await page.goto(URLS.person(PEOPLE.visitedFully), { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(2000)
    const profileText = await innerTextSafe(page)
    const hasCardContent = await page
      .locator('[data-profile-card-wrapper="true"], [data-profile-empty-state]')
      .count()
    checkProfile.textSnippet = profileText.slice(0, 300)
    checkProfile.hasCardContent = hasCardContent > 0
    checkProfile.pass = !/page not found/i.test(profileText) && hasCardContent > 0
    checkProfile.symptom = checkProfile.pass
      ? 'profile header + bento content rendered online'
      : 'profile did not render bento content online (see hasCardContent)'
    checkProfile.screenshot = await shot(page, 'smoke-profile-online')
    result.checks.push(checkProfile)

    // Background prefetch completes with plausible counts
    let checkPrefetch = { name: 'background prefetch "done" log with plausible counts' }
    const prefetch = await waitForPrefetchDone(prefetchLog, { timeoutMs: 45000 })
    checkPrefetch.prefetch = prefetch
    checkPrefetch.pass = Boolean(
      prefetch.sawDone &&
      prefetch.counts &&
      prefetch.counts.members > 0 &&
      prefetch.counts.profiles > 0 &&
      prefetch.counts.bento > 0,
    )
    checkPrefetch.symptom = checkPrefetch.pass
      ? `plausible counts: ${JSON.stringify(prefetch.counts)}`
      : `no plausible "done" log seen: ${JSON.stringify(prefetch)}`
    result.checks.push(checkPrefetch)

    // No new console errors beyond the known socket.io :9000 refusal. Every "Failed to load
    // resource" console error should be accounted for by an equal number of :9000 socket.io
    // requestfailed events (see the listener above) — anything left over is unexpected.
    const failedResourceErrors = consoleErrors.filter((e) => e.includes('Failed to load resource'))
    const otherConsoleErrors = consoleErrors.filter((e) => !e.includes('Failed to load resource'))
    const unexplainedFailedResourceCount = Math.max(
      0,
      failedResourceErrors.length - socketIoFailures,
    )
    result.socketIoFailures = socketIoFailures
    result.checks.push({
      name: 'no unexpected console errors',
      pass:
        unexplainedFailedResourceCount === 0 &&
        otherConsoleErrors.length === 0 &&
        pageErrors.length === 0,
      symptom:
        unexplainedFailedResourceCount === 0 &&
        otherConsoleErrors.length === 0 &&
        pageErrors.length === 0
          ? `only the known socket.io :9000 refusal (${socketIoFailures} request(s)), zero uncaught exceptions`
          : `unexplained failed-resource errors=${unexplainedFailedResourceCount}, other console errors=${JSON.stringify(otherConsoleErrors)}, pageErrors=${JSON.stringify(pageErrors)}`,
    })

    result.pass = result.checks.every((c) => c.pass)
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    result.prefetchLog = prefetchLog
    await browser.close()
  }

  writeResult('smoke-online-people', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
