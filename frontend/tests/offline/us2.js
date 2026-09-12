// US2 — Read what I've seen: after warming feed / space discussion list / discussion,
// go offline and revisit each via both reload and client-side nav; cached content
// (title/body/comments/list items) should be visible, no infinite spinner/error screen.
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

const EXPECTED = {
  discussionTitle: 'Capsule art, near-final, need eyes before it goes on the page',
  spaceTitle: 'Art',
}

function textCheck(text, needle) {
  return text.toLowerCase().includes(needle.toLowerCase())
}

async function evaluateContent(page, name, requiredSnippets) {
  await page.waitForTimeout(2000)
  const info = await appRootInfo(page)
  const text = await innerTextSafe(page)
  const screenshot = await shot(page, name)
  const foundSnippets = requiredSnippets.filter((s) => textCheck(text, s))
  const missingSnippets = requiredSnippets.filter((s) => !textCheck(text, s))
  const looksLikeSpinnerOnly = /^\s*$/.test(text) || text.trim().length < 5
  const landedOnOnboarding = page.url().includes('/onboarding')
  return {
    url: page.url(),
    info,
    screenshot,
    textSnippet: text.slice(0, 400),
    foundSnippets,
    missingSnippets,
    looksLikeSpinnerOnly,
    landedOnOnboarding,
    pass:
      info.appExists &&
      info.appChildCount > 0 &&
      missingSnippets.length === 0 &&
      !landedOnOnboarding,
  }
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US2', checks: [] }

  try {
    result.warmup = await warmup(page)
    await context.setOffline(true)

    // --- Reload-based checks (fresh navigation while offline) ---
    for (const [label, url, snippets] of [
      ['reload feed', URLS.feed, ['Common Room']],
      ['reload space discussions', URLS.spaceDiscussions, [EXPECTED.spaceTitle]],
      ['reload discussion', URLS.discussion, [EXPECTED.discussionTitle]],
    ]) {
      let check = { name: label, mode: 'reload' }
      try {
        await page.goto(url, { waitUntil: 'load', timeout: 8000 })
        Object.assign(
          check,
          await evaluateContent(page, `us2-${label.replace(/\s+/g, '-')}`, snippets),
        )
        check.symptom = check.pass
          ? 'cached content visible'
          : check.landedOnOnboarding
            ? 'redirected to /g/onboarding instead of showing cached feed content'
            : check.looksLikeSpinnerOnly
              ? 'blank / spinner-only, no content'
              : `missing expected text: ${check.missingSnippets.join(', ') || '(app root did not mount)'}`
      } catch (e) {
        check.pass = false
        check.symptom = `navigation threw: ${e.message}`
        check.screenshot = await shot(page, `us2-${label.replace(/\s+/g, '-')}-error`)
      }
      result.checks.push(check)
    }

    // --- Client-side navigation checks (SPA nav while offline, starting from the
    // discussion page which we know loads from the reload check above) ---
    let clientNavOk = true
    try {
      await page.goto(URLS.discussion, { waitUntil: 'load', timeout: 8000 })
      await page.waitForTimeout(1500)
    } catch (e) {
      clientNavOk = false
      result.checks.push({
        name: 'client-nav setup (load discussion)',
        mode: 'client-nav',
        pass: false,
        symptom: `could not establish SPA starting point offline: ${e.message}`,
      })
    }

    if (clientNavOk) {
      for (const [label, url, snippets] of [
        ['client-nav to space discussions', URLS.spaceDiscussions, [EXPECTED.spaceTitle]],
        ['client-nav to feed', URLS.feed, ['Common Room']],
        ['client-nav back to discussion', URLS.discussion, [EXPECTED.discussionTitle]],
      ]) {
        let check = { name: label, mode: 'client-nav' }
        try {
          // Use page.evaluate + history/router link click semantics via direct goto with
          // waitUntil 'commit' would still be a browser navigation; to truly exercise SPA
          // client-side routing we click an in-app link where possible. Falling back to
          // page.goto with 'commit' (not 'load') most closely emulates a client nav wait
          // profile without forcing a full reload wait, but Playwright's goto is always a
          // real navigation. We accept this as "navigation" coverage; a dedicated in-app
          // link click is used for at least one hop below for genuine SPA-nav evidence.
          await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 8000 })
          Object.assign(
            check,
            await evaluateContent(page, `us2-${label.replace(/\s+/g, '-')}`, snippets),
          )
          check.symptom = check.pass
            ? 'cached content visible'
            : check.landedOnOnboarding
              ? 'redirected to /g/onboarding instead of showing cached feed content'
              : check.looksLikeSpinnerOnly
                ? 'blank / spinner-only, no content'
                : `missing expected text: ${check.missingSnippets.join(', ') || '(app root did not mount)'}`
        } catch (e) {
          check.pass = false
          check.symptom = `navigation threw: ${e.message}`
          check.screenshot = await shot(page, `us2-${label.replace(/\s+/g, '-')}-error`)
        }
        result.checks.push(check)
      }

      // Genuine in-app SPA link click: from space discussions list, click the seeded
      // discussion row and confirm it opens client-side (no full navigation) while offline.
      let clickCheck = {
        name: 'in-app link click: space list -> discussion',
        mode: 'client-nav-click',
      }
      try {
        await page.goto(URLS.spaceDiscussions, { waitUntil: 'load', timeout: 8000 })
        await page.waitForTimeout(1500)
        const link = page.locator(`a[href*="/discussion/55"]`).first()
        const linkVisible = await link.isVisible().catch(() => false)
        clickCheck.linkVisible = linkVisible
        if (linkVisible) {
          await link.click()
          await page.waitForTimeout(1500)
          Object.assign(
            clickCheck,
            await evaluateContent(page, 'us2-click-into-discussion', [EXPECTED.discussionTitle]),
          )
          clickCheck.symptom = clickCheck.pass
            ? 'cached content visible after client-side link click'
            : clickCheck.landedOnOnboarding
              ? 'redirected to /g/onboarding instead of the discussion'
              : `missing expected text: ${clickCheck.missingSnippets?.join(', ') || '(app root did not mount)'}`
        } else {
          clickCheck.pass = false
          clickCheck.symptom = 'discussion row link not found/visible in cached space list'
          clickCheck.screenshot = await shot(page, 'us2-click-into-discussion-no-link')
        }
      } catch (e) {
        clickCheck.pass = false
        clickCheck.symptom = `click nav threw: ${e.message}`
      }
      result.checks.push(clickCheck)
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

  writeResult('us2', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
