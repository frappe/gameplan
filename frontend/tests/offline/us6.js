// US6 — Honest dead ends: offline navigation to content never visited before should
// show a friendly "can't load this while offline" state with retry — not a blank
// screen, crash, or infinite spinner.
const {
  chromium,
  URLS,
  newLoggedInContext,
  warmup,
  shot,
  innerTextSafe,
  appRootInfo,
  writeResult,
} = require('./helpers')

async function looksLikeFriendlyFallback(text) {
  return /offline|not available|can.?t load|unable to load|no connection|try again|retry/i.test(
    text,
  )
}

async function checkSpinnerStillSpinning(page) {
  // Sample the DOM twice, ~1.5s apart, looking for animate-pulse/animate-spin
  // markers that never resolve — a crude "infinite spinner" detector.
  const sample = () =>
    page.evaluate(() => {
      const spinners = document.querySelectorAll('.animate-spin, .animate-pulse, [role="status"]')
      return spinners.length
    })
  const a = await sample()
  await page.waitForTimeout(4000)
  const b = await sample()
  return { first: a, second: b, stillPresent: a > 0 && b > 0 }
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US6', checks: [] }

  try {
    result.warmup = await warmup(page)
    await context.setOffline(true)

    for (const [label, url] of [
      ['never-visited discussion', URLS.uncachedDiscussion],
      ['never-visited space', URLS.uncachedSpace],
    ]) {
      let check = { name: label, url }
      const errCountBefore = pageErrors.length
      try {
        await page.goto(url, { waitUntil: 'load', timeout: 10000 }).catch((e) => {
          check.gotoError = String(e)
        })
        await page.waitForTimeout(2500)

        const info = await appRootInfo(page)
        const text = await innerTextSafe(page)
        const spinner = await checkSpinnerStillSpinning(page)
        const friendly = await looksLikeFriendlyFallback(text)
        const newPageErrors = pageErrors.slice(errCountBefore)
        const isBlank = !info.appExists || info.appChildCount === 0 || text.trim().length < 5

        check.info = info
        check.textSnippet = text.slice(0, 400)
        check.friendlyFallbackDetected = friendly
        check.isBlank = isBlank
        check.infiniteSpinner = spinner.stillPresent
        check.newPageErrors = newPageErrors
        check.screenshot = await shot(page, `us6-${label.replace(/\s+/g, '-')}`)

        check.pass = friendly && !isBlank && !spinner.stillPresent && newPageErrors.length === 0
        check.symptom = check.pass
          ? 'friendly offline fallback shown with no crash/spinner'
          : isBlank
            ? 'blank page (no friendly fallback)'
            : spinner.stillPresent
              ? 'infinite spinner — content never resolved'
              : newPageErrors.length > 0
                ? `uncaught exception(s): ${newPageErrors.join(' | ')}`
                : 'no offline/retry/"not available" messaging detected — page rendered something else'
      } catch (e) {
        check.pass = false
        check.symptom = `threw: ${e.message}`
        check.screenshot = await shot(page, `us6-${label.replace(/\s+/g, '-')}-error`)
      }
      result.checks.push(check)
    }

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

  writeResult('us6', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
