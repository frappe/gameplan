// US4 — Don't lose my words: offline comment submit should fail gracefully (error
// surfaced, text preserved in the editor), then succeed once back online.
const {
  chromium,
  URLS,
  newLoggedInContext,
  newApiRequestContext,
  warmup,
  shot,
  writeResult,
} = require('./helpers')

const MARKER = `offline-us4-${Date.now()}`
const DISTINCTIVE_TEXT = `Testing offline comment preservation ${MARKER}`

async function openComposer(page) {
  const addCommentBtn = page.locator('button:has-text("Add a comment")').first()
  if (await addCommentBtn.isVisible().catch(() => false)) {
    await addCommentBtn.click()
    await page.waitForTimeout(300)
  }
}

async function getEditor(page) {
  // The comment composer's ProseMirror/TipTap root; last contenteditable on the
  // page corresponds to the new-comment box (existing comments render read-only).
  return page.locator('[contenteditable="true"]').last()
}

async function getVisibleSubmitButton(page) {
  // The composer renders both a Comment submit and a (v-show hidden) Poll submit
  // button with the same text; `:visible` filters out the inactive tab's button.
  return page.locator('button:has-text("Submit"):visible').last()
}

async function bodyTextSnapshot(page) {
  try {
    return await page.evaluate(() => document.body.innerText)
  } catch {
    return ''
  }
}

function findNewErrorText(before, after) {
  const re = /(fail|error|offline|network|could not|try again|unable|no internet|not connected)/i
  const beforeLines = new Set(
    before
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean),
  )
  const afterLines = after
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
  return afterLines.filter((l) => re.test(l) && !beforeLines.has(l))
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US4', checks: [] }
  let createdCommentName = null

  try {
    result.warmup = await warmup(page)
    await page.goto(URLS.discussion, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1500)
    await openComposer(page)

    await context.setOffline(true)

    const editor = await getEditor(page)
    let check1 = { name: 'offline submit fails gracefully, text preserved' }
    try {
      await editor.click({ timeout: 8000 })
      await page.keyboard.type(DISTINCTIVE_TEXT, { delay: 10 })
      await page.waitForTimeout(300)

      const beforeSubmitText = await bodyTextSnapshot(page)
      const submitBtn = await getVisibleSubmitButton(page)
      await submitBtn.click({ timeout: 8000 }).catch((e) => {
        check1.clickError = String(e)
      })
      await page.waitForTimeout(2000)
      const afterSubmitText = await bodyTextSnapshot(page)

      const newErrorLines = findNewErrorText(beforeSubmitText, afterSubmitText)
      const editorTextAfter = await editor.innerText().catch(() => '')
      const textPreserved = editorTextAfter.includes(DISTINCTIVE_TEXT)

      check1.newErrorLines = newErrorLines
      check1.textPreserved = textPreserved
      check1.editorTextAfter = editorTextAfter.slice(0, 300)
      check1.screenshot = await shot(page, 'us4-offline-submit-attempt')
      check1.pass = newErrorLines.length > 0 && textPreserved
      check1.symptom = check1.pass
        ? `error shown (${newErrorLines[0]}) and text preserved`
        : !textPreserved
          ? 'typed text was lost from the editor after failed submit (silent data loss)'
          : 'no visible error/toast surfaced after offline submit attempt'
    } catch (e) {
      check1.pass = false
      check1.symptom = `threw: ${e.message}`
      check1.screenshot = await shot(page, 'us4-offline-submit-error')
    }
    result.checks.push(check1)

    // Now go online and resubmit — should succeed.
    let check2 = { name: 'submit succeeds after reconnect' }
    try {
      await context.setOffline(false)
      await page.waitForTimeout(1500)

      // The offline-failure toast from check1 is a real sonner Toast whose
      // auto-dismiss timer is paused while `document.visibilityState` isn't
      // "visible" (vue-sonner's `isDocumentHidden` gate) — headless Chromium
      // pages can sit in that state indefinitely, so the toast lingers over
      // the Submit button far longer than the 4s TOAST_LIFETIME a real,
      // focused tab would give it. Dismiss it explicitly (same action a real
      // user would take) rather than waiting on a timer that may never fire
      // in this environment.
      const closeButtons = page.locator('[data-close-button="true"]')
      const closeCount = await closeButtons.count().catch(() => 0)
      for (let i = 0; i < closeCount; i++) {
        await closeButtons
          .first()
          .click({ timeout: 2000 })
          .catch(() => {})
      }
      await page.waitForTimeout(300)

      const submitBtn = await getVisibleSubmitButton(page)
      const editorNow = await getEditor(page)
      const editorTextNow = await editorNow.innerText().catch(() => '')
      check2.editorTextBeforeRetry = editorTextNow.slice(0, 300)

      if (!editorTextNow.includes(DISTINCTIVE_TEXT)) {
        check2.pass = false
        check2.symptom =
          'skipped: distinctive text was not present in editor to resubmit (see check1)'
      } else {
        await submitBtn.click({ timeout: 8000 })
        await page.waitForTimeout(2500)
        const pageText = await bodyTextSnapshot(page)
        check2.commentAppeared = pageText.includes(DISTINCTIVE_TEXT)
        check2.screenshot = await shot(page, 'us4-online-resubmit')
        check2.pass = check2.commentAppeared
        check2.symptom = check2.pass
          ? 'comment posted successfully after reconnect'
          : 'comment did not appear after resubmitting online'

        if (check2.commentAppeared) {
          // Find the created comment's name via API for cleanup.
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
          await api.dispose()
        }
      }
    } catch (e) {
      check2.pass = false
      check2.symptom = `threw: ${e.message}`
      check2.screenshot = await shot(page, 'us4-online-resubmit-error')
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

    // Cleanup: delete the comment we created during this test, if any.
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
      result.cleanup = 'no comment created (or name lookup failed) — nothing to delete'
    }
  }

  writeResult('us4', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
