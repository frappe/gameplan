// US3 — Know I'm offline: an indicator should appear when offline and clear on
// reconnect. We search broadly (role=status/alert, common banner/toast/pill classes,
// and any element whose text matches /offline/i) since we don't know the exact
// implementation up front.
const {
  chromium,
  URLS,
  EMAIL,
  newLoggedInContext,
  warmup,
  shot,
  writeResult,
} = require('./helpers')

// The seeded test account's own username ("offline-tester") literally contains
// "offline" and renders on the page regardless of connectivity (header/sidebar/hover
// cards showing the signed-in user's name) — exclude an exact match on it so it can't
// masquerade as the real connectivity indicator below.
const USERNAME = EMAIL.split('@')[0]

async function findOfflineIndicator(page, excludeExact) {
  return page.evaluate((exclude) => {
    const re = /offline|you.?re offline|showing saved|no connection|reconnect/i
    const candidates = []
    const all = document.querySelectorAll('body *')
    for (const el of all) {
      // Only leaf-ish elements with direct text, to avoid matching giant containers.
      const text = el.textContent?.trim() || ''
      if (!text || text.length > 200) continue
      if (re.test(text)) {
        const ownText = Array.from(el.childNodes)
          .filter((n) => n.nodeType === Node.TEXT_NODE)
          .map((n) => n.textContent)
          .join('')
          .trim()
        if (ownText && re.test(ownText) && ownText.toLowerCase() !== exclude.toLowerCase()) {
          const rect = el.getBoundingClientRect()
          candidates.push({
            tag: el.tagName,
            class: el.className?.toString?.() || '',
            text: ownText.slice(0, 200),
            visible: rect.width > 0 && rect.height > 0,
            role: el.getAttribute('role'),
          })
        }
      }
    }
    return candidates
  }, excludeExact)
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US3', checks: [] }

  try {
    result.warmup = await warmup(page)

    // Baseline (online): no offline indicator should be present.
    const onlineCandidates = await findOfflineIndicator(page, USERNAME)
    result.onlineBaseline = { candidates: onlineCandidates }

    await context.setOffline(true)
    // Give any 'offline'/'online' event listener a moment to react (no reload —
    // this exercises the live indicator, not a reload-triggered one).
    await page.waitForTimeout(3000)
    // Nudge in case the app only reacts to navigation/focus rather than the
    // browser 'offline' event.
    await page.evaluate(() => window.dispatchEvent(new Event('offline')))
    await page.waitForTimeout(1000)

    const offlineCandidates = await findOfflineIndicator(page, USERNAME)
    const offlineShot = await shot(page, 'us3-offline-indicator-search')
    const visibleOfflineCandidates = offlineCandidates.filter((c) => c.visible)

    let check1 = {
      name: 'indicator appears when offline',
      candidates: offlineCandidates,
      screenshot: offlineShot,
      pass: visibleOfflineCandidates.length > 0,
    }
    check1.symptom = check1.pass
      ? `found ${visibleOfflineCandidates.length} visible offline-related element(s)`
      : 'no offline indicator UI exists anywhere in the DOM (searched all elements for /offline|reconnect|no connection/i text)'
    result.checks.push(check1)

    // Go back online and check the indicator clears (only meaningful if one appeared).
    await context.setOffline(false)
    await page.evaluate(() => window.dispatchEvent(new Event('online')))
    await page.waitForTimeout(3000)
    const afterOnlineCandidates = await findOfflineIndicator(page, USERNAME)
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
