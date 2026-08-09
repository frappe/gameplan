// US1 — Launch offline: reload /g and a deep link while offline; app shell should
// render instead of the browser's net::ERR page.
const {
  chromium,
  URLS,
  newLoggedInContext,
  warmup,
  shot,
  appRootInfo,
  writeResult,
} = require('./helpers')

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US1', checks: [] }

  try {
    result.warmup = await warmup(page)

    await context.setOffline(true)

    // Check 1: reload /g while offline.
    let check1 = { name: 'reload /g offline' }
    try {
      await page.goto(URLS.feed, { waitUntil: 'load', timeout: 8000 })
      await page.waitForTimeout(1500)
      check1.info = await appRootInfo(page)
      check1.screenshot = await shot(page, 'us1-reload-feed')
      check1.pass = check1.info.appExists && check1.info.appChildCount > 0
      check1.symptom = check1.pass
        ? 'app shell rendered'
        : `blank/unmounted app root (appExists=${check1.info.appExists}, children=${check1.info.appChildCount})`
    } catch (e) {
      check1.pass = false
      check1.symptom = `navigation threw: ${e.message}`
      check1.screenshot = await shot(page, 'us1-reload-feed-error')
    }
    result.checks.push(check1)

    // Check 2: reload the discussion deep link while offline.
    let check2 = { name: 'reload discussion deep link offline' }
    try {
      await page.goto(URLS.discussion, { waitUntil: 'load', timeout: 8000 })
      await page.waitForTimeout(1500)
      check2.info = await appRootInfo(page)
      check2.screenshot = await shot(page, 'us1-reload-discussion')
      check2.pass = check2.info.appExists && check2.info.appChildCount > 0
      check2.symptom = check2.pass
        ? 'app shell rendered'
        : `blank/unmounted app root (appExists=${check2.info.appExists}, children=${check2.info.appChildCount})`
    } catch (e) {
      check2.pass = false
      check2.symptom = `navigation threw: ${e.message}`
      check2.screenshot = await shot(page, 'us1-reload-discussion-error')
    }
    result.checks.push(check2)

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

  writeResult('us1', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
