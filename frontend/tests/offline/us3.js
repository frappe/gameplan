// US3 — Know I'm offline: an indicator should appear when offline and clear on
// reconnect. Looks for the banner OfflineIndicator.vue renders (a role=status element
// reading "Offline") rather than any text matching /offline/i, which also matched the test
// account's own name ("Offline Tester") and so always looked offline.
const { chromium, newLoggedInContext, warmup, shot, writeResult } = require('./helpers')

function findOfflineBanner(page) {
  return page.evaluate(() =>
    [...document.querySelectorAll('[role="status"]')]
      .filter((el) => /^offline$/i.test(el.textContent.trim()))
      .map((el) => {
        const rect = el.getBoundingClientRect()
        return { text: el.textContent.trim(), visible: rect.width > 0 && rect.height > 0 }
      }),
  )
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US3', checks: [] }

  try {
    result.warmup = await warmup(page)

    // Baseline (online): no offline indicator should be present.
    const onlineCandidates = await findOfflineBanner(page)
    result.onlineBaseline = { candidates: onlineCandidates }

    await context.setOffline(true)
    // Give any 'offline'/'online' event listener a moment to react (no reload —
    // this exercises the live indicator, not a reload-triggered one).
    await page.waitForTimeout(3000)
    // Nudge in case the app only reacts to navigation/focus rather than the
    // browser 'offline' event.
    await page.evaluate(() => window.dispatchEvent(new Event('offline')))
    await page.waitForTimeout(1000)

    const offlineCandidates = await findOfflineBanner(page)
    const offlineShot = await shot(page, 'us3-offline-indicator-search')
    const visibleOfflineCandidates = offlineCandidates.filter((c) => c.visible)

    let check1 = {
      name: 'indicator appears when offline',
      candidates: offlineCandidates,
      screenshot: offlineShot,
      pass: visibleOfflineCandidates.length > 0,
    }
    check1.symptom = check1.pass
      ? 'offline banner shown'
      : 'no visible offline banner (role=status reading "Offline")'
    result.checks.push(check1)

    // Go back online and check the indicator clears (only meaningful if one appeared).
    await context.setOffline(false)
    await page.evaluate(() => window.dispatchEvent(new Event('online')))
    await page.waitForTimeout(3000)
    const afterOnlineCandidates = await findOfflineBanner(page)
    const stillVisible = afterOnlineCandidates.filter((c) => c.visible)
    const afterOnlineShot = await shot(page, 'us3-after-reconnect')

    let check2 = {
      name: 'indicator clears on reconnect',
      candidates: afterOnlineCandidates,
      screenshot: afterOnlineShot,
      // Only a meaningful pass if an indicator existed in the first place.
      pass: check1.pass ? stillVisible.length === 0 : null,
    }
    check2.symptom = !check1.pass
      ? 'n/a — no indicator existed to clear'
      : check2.pass
        ? 'indicator cleared after reconnect'
        : 'indicator still visible after going back online'
    result.checks.push(check2)

    result.pass = check1.pass && (check2.pass === null || check2.pass === true)
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    await context.setOffline(false).catch(() => {})
    await browser.close()
  }

  writeResult('us3', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
