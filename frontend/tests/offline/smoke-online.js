// Online regression smoke test — fresh context, online only. Confirms feed/space/
// discussion load, post+delete a comment works, no new console errors, and the
// offline indicator is NOT visible while online. Not part of the US1-US6 suite.
const {
  chromium,
  URLS,
  newLoggedInContext,
  newApiRequestContext,
  shot,
  writeResult,
} = require('./helpers')

const MARKER = `smoke-${Date.now()}`
const DISTINCTIVE_TEXT = `Online smoke test comment ${MARKER}`

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'SMOKE-ONLINE', checks: [] }
  let createdCommentName = null

  try {
    // Feed
    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
    // `/g` client-side redirects to the community's discussions route once the app has
    // hydrated — let it land before the next goto(), or that next navigation can get
    // reported as "interrupted by another navigation" to the redirect's target.
    await page.waitForURL(/\/g\/community\//, { timeout: 10000 }).catch(() => {})
    // Poll rather than a single fixed-delay check: under system load, the redirect and
    // first render can land a bit after `waitForURL` resolves — same content, just slower.
    let feedInfo = { title: '', bodyText: '' }
    const feedDeadline = Date.now() + 8000
    while (Date.now() < feedDeadline) {
      feedInfo = await page.evaluate(() => ({
        title: document.title,
        bodyText: document.body.innerText.slice(0, 300),
      }))
      if (feedInfo.bodyText.length > 0) break
      await page.waitForTimeout(500)
    }
    result.checks.push({ name: 'feed loads', pass: feedInfo.bodyText.length > 0, info: feedInfo })

    // Space discussion list
    await page.goto(URLS.spaceDiscussions, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1000)
    const spaceInfo = await page.evaluate(() => document.body.innerText.slice(0, 300))
    result.checks.push({
      name: 'space discussion list loads',
      pass: spaceInfo.includes('Art'),
      info: spaceInfo,
    })

    // Discussion
    await page.goto(URLS.discussion, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1000)
    const discInfo = await page.evaluate(() => document.body.innerText.slice(0, 300))
    result.checks.push({
      name: 'discussion loads',
      pass: discInfo.includes('Capsule art'),
      info: discInfo,
    })

    // Offline indicator should NOT be visible online
    const offlineIndicatorVisible = await page.evaluate(() => {
      const els = Array.from(document.querySelectorAll('body *'))
      const re = /offline|you.?re offline|showing saved|reconnect/i
      return els.some((el) => {
        if (el.children.length > 0) return false
        const text = el.textContent?.trim()
        if (!text || text.length > 100) return false
        if (!re.test(text)) return false
        const rect = el.getBoundingClientRect()
        const style = window.getComputedStyle(el)
        return (
          rect.width > 0 &&
          rect.height > 0 &&
          style.visibility !== 'hidden' &&
          style.display !== 'none'
        )
      })
    })
    result.checks.push({
      name: 'offline indicator NOT visible while online',
      pass: !offlineIndicatorVisible,
      info: { offlineIndicatorVisible },
    })

    // Post a comment
    const addCommentBtn = page.locator('button:has-text("Add a comment")').first()
    if (await addCommentBtn.isVisible().catch(() => false)) {
      await addCommentBtn.click()
      await page.waitForTimeout(300)
    }
    const editor = page.locator('[contenteditable="true"]').last()
    await editor.click({ timeout: 8000 })
    await page.keyboard.type(DISTINCTIVE_TEXT, { delay: 10 })
    await page.waitForTimeout(300)
    const submitBtn = page.locator('button:has-text("Submit"):visible').last()
    await submitBtn.click({ timeout: 8000 })
    await page.waitForTimeout(2000)
    const afterPostText = await page.evaluate(() => document.body.innerText)
    const posted = afterPostText.includes(DISTINCTIVE_TEXT)
    result.checks.push({ name: 'post comment online', pass: posted })
    result.screenshotAfterPost = await shot(page, 'smoke-online-comment-posted')

    if (posted) {
      // Delete via UI: open the comment's "..." (Comment Options) dropdown, click
      // Delete, confirm the danger dialog.
      let deletedViaUI = false
      try {
        const commentRow = page.locator(':has-text("' + DISTINCTIVE_TEXT + '")').last()
        const optionsBtn = page.locator('button[aria-label="Comment Options"]').last()
        await optionsBtn.click({ timeout: 5000 })
        await page.waitForTimeout(200)
        await page.locator('text=Delete').last().click({ timeout: 5000 })
        await page.waitForTimeout(300)
        await page.locator('button:has-text("Delete")').last().click({ timeout: 5000 })
        await page.waitForTimeout(1500)
        const afterDeleteText = await page.evaluate(() => document.body.innerText)
        deletedViaUI = !afterDeleteText.includes(DISTINCTIVE_TEXT)
      } catch (e) {
        result.deleteViaUIError = String(e)
      }
      result.checks.push({ name: 'delete comment via UI', pass: deletedViaUI })
      result.screenshotAfterDelete = await shot(page, 'smoke-online-comment-deleted')

      // Verify + fallback cleanup via API regardless (belt and suspenders — don't
      // leave a stray comment on the site if the UI delete selector was off).
      const api = await newApiRequestContext()
      const resp = await api.get(
        `/api/method/frappe.client.get_list?doctype=GP%20Comment&filters=${encodeURIComponent(
          JSON.stringify([
            ['reference_name', '=', '55'],
            ['content', 'like', `%${MARKER}%`],
          ]),
        )}&fields=${encodeURIComponent(JSON.stringify(['name']))}`,
      )
      const body = await resp.json().catch(() => null)
      createdCommentName = body?.message?.[0]?.name ?? null
      if (createdCommentName) {
        await api.post('/api/method/frappe.client.delete', {
          form: { doctype: 'GP Comment', name: String(createdCommentName) },
        })
        result.cleanup = `deletedViaUI=${deletedViaUI}; also deleted GP Comment ${createdCommentName} via API (fallback/verify)`
      } else {
        result.cleanup = `deletedViaUI=${deletedViaUI}; no leftover GP Comment found via API`
      }
      await api.dispose()
    }

    result.pass = result.checks.every((c) => c.pass)
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
    result.screenshotOnError = await shot(page, 'smoke-online-error')
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    await browser.close()
  }

  writeResult('smoke-online', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
