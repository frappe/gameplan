// US9 — Download for offline: picking "Past week" in Settings > Offline downloads the
// discussions from joined spaces with recent activity, so one never opened before reads
// offline with its comments. Content outside the window still shows the honest offline
// fallback, the download costs about one request per 20 discussions, and a reload soon after
// doesn't download again.
const {
  chromium,
  BASE,
  URLS,
  newLoggedInContext,
  newApiRequestContext,
  idbKeyvalKeys,
  innerTextSafe,
  shot,
  writeResult,
} = require('./helpers')
const { COMMUNITY, JOINED_SPACE_ID } = require('./config')

const MARKER = `us9-${Date.now()}`
const OFFLINE_API = /gameplan\.offline_downloads\.get_offline_(index|bundle)/

async function createDiscussion(api) {
  const discussion = await api.post('/api/v2/document/GP Discussion', {
    data: {
      title: `${MARKER} downloaded thread`,
      project: JOINED_SPACE_ID,
      content: '<p>Body</p>',
    },
  })
  if (!discussion.ok()) throw new Error(`create discussion: ${await discussion.text()}`)
  const name = String((await discussion.json()).data.name)
  const comment = await api.post('/api/v2/document/GP Comment', {
    data: {
      reference_doctype: 'GP Discussion',
      reference_name: name,
      content: `<p>${MARKER} reply</p>`,
    },
  })
  if (!comment.ok()) throw new Error(`create comment: ${await comment.text()}`)
  return name
}

function spaNavigate(page, path) {
  return page.evaluate((p) => {
    history.pushState({}, '', p)
    dispatchEvent(new PopStateEvent('popstate', { state: history.state }))
  }, path)
}

async function run() {
  const api = await newApiRequestContext()
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US9', checks: [] }
  const offlineRequests = []
  page.on('request', (req) => {
    if (OFFLINE_API.test(req.url())) offlineRequests.push(req.url())
  })
  let created = null

  try {
    created = await createDiscussion(api)
    const discussionPath = `/g/community/${COMMUNITY}/space/${JOINED_SPACE_ID}/discussion/${created}`

    await page.goto(`${BASE}/g/settings/offline`, { waitUntil: 'load', timeout: 20000 })
    await page.getByText('Download for offline').waitFor({ timeout: 15000 })
    await page.getByRole('combobox').first().click()
    await page.getByRole('option', { name: 'Past week' }).click()
    await page
      .getByText('Discussions are ready to read offline')
      .waitFor({ timeout: 30000 })
      .catch(() => {})

    const keys = await idbKeyvalKeys(page)
    const index = await (
      await api.post('/api/method/gameplan.offline_downloads.get_offline_index', {
        data: { window_days: 7 },
      })
    ).json()
    const expectedRequests = 1 + Math.max(1, Math.ceil(index.message.discussions.length / 20))
    result.checks.push({
      name: 'the new discussion and its comments are stored in the app caches',
      pass:
        keys.includes(`doc:GP Discussion/${created}`) &&
        keys.some((key) => key.includes('"Comments"') && key.includes(`"${created}"`)),
      symptom: `downloaded keys for ${created}: ${keys.filter((k) => String(k).includes(created)).length}`,
    })
    result.checks.push({
      name: 'the download costs one index call plus one call per 20 discussions',
      pass: offlineRequests.length === expectedRequests,
      symptom: `${offlineRequests.length} offline-download requests, expected ${expectedRequests}`,
    })

    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(2000)
    await context.setOffline(true)
    await page.waitForTimeout(500)

    await spaNavigate(page, discussionPath)
    await page.waitForTimeout(2500)
    const text = await innerTextSafe(page)
    result.checks.push({
      name: 'a never-opened discussion in the window reads offline with its reply',
      pass: text.includes(`${MARKER} downloaded thread`) && text.includes(`${MARKER} reply`),
      symptom: text.slice(0, 300),
      screenshot: await shot(page, 'us9-downloaded-discussion-offline'),
    })

    await spaNavigate(page, new URL(URLS.uncachedDiscussion).pathname)
    await page.waitForTimeout(2500)
    const outside = await innerTextSafe(page)
    result.checks.push({
      name: 'a discussion outside the window still shows the offline fallback',
      pass: /isn.?t available offline|can.?t load/i.test(outside),
      symptom: outside.slice(0, 300),
    })

    await context.setOffline(false)
    offlineRequests.length = 0
    await page.reload({ waitUntil: 'load' })
    // The first background sync waits up to 35s after load.
    await page.waitForTimeout(40000)
    result.checks.push({
      name: 'a reload soon after a complete sync does not download again',
      pass: offlineRequests.length === 0,
      symptom: `${offlineRequests.length} offline-download requests after reload`,
    })

    result.pass = result.checks.every((check) => check.pass)
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    await context.setOffline(false).catch(() => {})
    if (created) await api.delete(`/api/v2/document/GP Discussion/${created}`).catch(() => {})
    await browser.close()
    await api.dispose()
  }

  writeResult('us9', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
