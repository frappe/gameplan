// US5 — Seamless recovery: content created elsewhere while we're offline should
// show up automatically after reconnect, without a hard reload.
const {
  chromium,
  URLS,
  newLoggedInContext,
  newApiRequestContext,
  warmup,
  shot,
  writeResult,
} = require('./helpers')

const MARKER = `offline-us5-${Date.now()}`
const DISTINCTIVE_TEXT = `US5 recovery probe comment ${MARKER}`

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US5', checks: [] }
  let createdCommentName = null

  try {
    result.warmup = await warmup(page)
    await page.goto(URLS.discussion, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1500)

    await context.setOffline(true)
    await page.waitForTimeout(500)

    // Create the comment via a fully separate, still-online APIRequestContext while
    // the page/context under test is offline.
    const api = await newApiRequestContext()
    const insertResp = await api.post('/api/method/frappe.client.insert', {
      form: {
        doc: JSON.stringify({
          doctype: 'GP Comment',
          reference_doctype: 'GP Discussion',
          reference_name: '55',
          content: `<p>${DISTINCTIVE_TEXT}</p>`,
        }),
      },
    })
    const insertOk = insertResp.ok()
    const insertBody = await insertResp.json().catch(() => null)
    createdCommentName = insertBody?.message?.name ?? null
    result.apiInsert = { ok: insertOk, status: insertResp.status(), name: createdCommentName }

    if (!insertOk || !createdCommentName) {
      result.pass = false
      result.fatalError = `Failed to create probe comment via API while offline: ${JSON.stringify(insertBody)}`
    } else {
      // Reconnect.
      await context.setOffline(false)
      const reconnectAt = Date.now()

      // Nudge the app the ways a real reconnect plausibly would, without navigating:
      // browser 'online' event, window focus, and document visibility.
      await page.evaluate(() => window.dispatchEvent(new Event('online')))
      await page.bringToFront()
      await page.evaluate(() => {
        window.dispatchEvent(new Event('focus'))
        document.dispatchEvent(new Event('visibilitychange'))
      })

      const deadlineMs = 30000
      const pollIntervalMs = 1000
      let appearedAt = null
      let lastText = ''
      while (Date.now() - reconnectAt < deadlineMs) {
        lastText = await page.evaluate(() => document.body.innerText).catch(() => '')
        if (lastText.includes(DISTINCTIVE_TEXT)) {
          appearedAt = Date.now()
          break
        }
        await page.waitForTimeout(pollIntervalMs)
      }

      const screenshot = await shot(page, 'us5-after-reconnect-wait')
      let check = {
        name: 'new content appears after reconnect without reload',
        waitedMs: appearedAt ? appearedAt - reconnectAt : deadlineMs,
        appeared: Boolean(appearedAt),
        navigationUsed: false,
        screenshot,
        lastBodyTextSnippet: lastText.slice(0, 400),
        pass: Boolean(appearedAt),
      }
      check.symptom = check.pass
        ? `appeared ${check.waitedMs}ms after reconnect (no reload, only online/focus/visibility events)`
        : `did not appear within ${deadlineMs}ms of reconnect without a reload`
      result.checks.push(check)

      // Diagnostic-only follow-up: does a client-side navigation/refetch pick it up,
      // to distinguish "no revalidation mechanism at all" from "revalidation is slower
      // than 30s"? Does not affect the US5 pass/fail above.
      if (!check.pass) {
        await page.goto(URLS.discussion, { waitUntil: 'load', timeout: 15000 })
        await page.waitForTimeout(1500)
        const afterNavText = await page.evaluate(() => document.body.innerText).catch(() => '')
        result.diagnosticAfterFullReload = {
          appearedAfterReload: afterNavText.includes(DISTINCTIVE_TEXT),
        }
      }

      result.pass = result.checks.every((c) => c.pass)
    }
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    await context.setOffline(false).catch(() => {})
    await browser.close()

    if (createdCommentName) {
      try {
        const api = await newApiRequestContext()
        await api.post('/api/method/frappe.client.delete', {
          form: { doctype: 'GP Comment', name: String(createdCommentName) },
        })
        await api.dispose()
        result.cleanup = `deleted GP Comment ${createdCommentName}`
      } catch (e) {
        result.cleanup = `FAILED to delete GP Comment ${createdCommentName}: ${e.message}`
      }
    } else {
      result.cleanup = 'no comment created — nothing to delete'
    }
  }

  writeResult('us5', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
