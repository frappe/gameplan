// Online regression smoke test (round 4 addition) — confirms this round's shared-computer
// safety + update-flow changes didn't break ordinary online usage: a plain login/logout
// cycle still works and lands on /login, and a completely fresh session sees NO update
// toast on first visit (no stale 'waiting' worker, no spurious controllerchange reload).
// Complements smoke-online.js (feed/space/discussion + comment) and
// smoke-online-people.js (People/profile + prefetch), which this does not repeat.
const { chromium, URLS, newLoggedInContext, logoutViaUI, shot, writeResult } = require('./helpers')

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'SMOKE-ONLINE-SHARED-COMPUTER', checks: [] }

  try {
    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1500)

    // No update toast on a fresh first visit (no prior SW version to diff against).
    const toastVisible = await page
      .locator('text=/A new version of Gameplan is available/i')
      .isVisible()
      .catch(() => false)
    result.checks.push({
      name: 'no update toast on first visit',
      pass: !toastVisible,
      symptom: toastVisible
        ? 'update toast unexpectedly shown on a fresh session'
        : 'no toast shown',
    })

    // Normal logout via the real UI path still works and lands on /login.
    let checkLogout = { name: 'logout via UI works, lands on /login' }
    try {
      await logoutViaUI(page)
      await page.waitForURL('**/login**', { timeout: 10000 })
      checkLogout.pass = true
      checkLogout.symptom = `redirected to ${page.url()}`
    } catch (e) {
      checkLogout.pass = false
      checkLogout.symptom = `threw: ${e.message}`
      checkLogout.screenshot = await shot(page, 'smoke-shared-computer-logout-error')
    }
    result.checks.push(checkLogout)

    result.pass = result.checks.every((c) => c.pass)
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    await browser.close()
  }

  writeResult('smoke-online-shared-computer', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
