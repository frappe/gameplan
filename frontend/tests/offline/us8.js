// US8 — Update flow: when a new service worker build lands while the app is open, the
// user should see a "new version available" toast (not a silent swap, and not a forced
// reload out from under them) with a Refresh action; clicking it should activate the new
// worker and reload exactly once (frontend/src/offline.ts's watchForUpdates/
// notifyUpdateAvailable/watchForControllerChange, gameplan-sw.js's install handler
// deliberately not calling self.skipWaiting() so an update sits in `waiting` until the
// user confirms).
//
// This test mutates the real gameplan-sw.js on disk (bumps CACHE_VERSION to the next
// integer, e.g. v7->v8), rebuilds, and reverts + rebuilds again in a `finally` —
// regardless of pass/fail — so it leaves the repo and the running dev server exactly as
// it found them for every other story in the suite. The version is read from the file
// rather than hardcoded so this doesn't drift out of sync with whatever CACHE_VERSION is
// actually committed.
const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')
const { chromium, URLS, newLoggedInContext, shot, writeResult } = require('./helpers')
const { APP_DIR } = require('./config')

const SW_FILE = path.join(APP_DIR, 'gameplan/www/gameplan-sw.js')

function readCurrentVersion() {
  const original = fs.readFileSync(SW_FILE, 'utf8')
  const m = original.match(/const CACHE_VERSION = "(v\d+)";/)
  if (!m) {
    throw new Error(`could not find a CACHE_VERSION line in ${SW_FILE} — file has drifted`)
  }
  return m[1]
}

function nextVersion(version) {
  const n = parseInt(version.slice(1), 10)
  return `v${n + 1}`
}

function bumpVersion(from, to) {
  const original = fs.readFileSync(SW_FILE, 'utf8')
  const marker = `const CACHE_VERSION = "${from}";`
  if (!original.includes(marker)) {
    throw new Error(`expected to find ${JSON.stringify(marker)} in ${SW_FILE} — file has drifted`)
  }
  fs.writeFileSync(SW_FILE, original.replace(marker, `const CACHE_VERSION = "${to}";`))
}

function build() {
  execSync('yarn build', { cwd: APP_DIR, stdio: 'pipe', timeout: 120000 })
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const { context, page, consoleErrors, pageErrors } = await newLoggedInContext(browser)
  const result = { story: 'US8', checks: [] }
  let bumped = false
  const FROM_VERSION = readCurrentVersion()
  const TO_VERSION = nextVersion(FROM_VERSION)

  try {
    // --- Baseline: the committed worker version active, controlling the page. ---
    await page.goto(URLS.feed, { waitUntil: 'load', timeout: 15000 })
    await page.waitForTimeout(1000)
    await page.evaluate(() => navigator.serviceWorker.ready.then(() => true)).catch(() => {})
    await page.waitForTimeout(4000) // warmLoadedAssets() follow-up timer

    const baselineController = await page.evaluate(() => ({
      scriptURL: navigator.serviceWorker.controller?.scriptURL ?? null,
      state: navigator.serviceWorker.controller?.state ?? null,
    }))
    const baselineCaches = await page.evaluate(() => caches.keys())
    result.baselineController = baselineController
    result.baselineCaches = baselineCaches
    result.checks.push({
      name: `baseline: ${FROM_VERSION} worker controls the page before the update`,
      pass:
        Boolean(baselineController.scriptURL) &&
        baselineCaches.some((n) => n.includes(`:${FROM_VERSION}:`)),
      symptom: `controller=${JSON.stringify(baselineController)} caches=${JSON.stringify(baselineCaches)}`,
    })

    // --- Ship a new SW build (bump CACHE_VERSION by one). ---
    bumpVersion(FROM_VERSION, TO_VERSION)
    bumped = true
    build()

    // --- Reload: the browser fetches the new SW bytes, byte-diffs, and (since install()
    // doesn't call skipWaiting()) parks the new worker in `waiting` rather than swapping
    // the controller. Force an explicit update() check too, rather than relying solely on
    // the browser's own navigation-triggered check, for determinism. ---
    await page.reload({ waitUntil: 'load', timeout: 15000 })
    await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.getRegistration('/g')
      await reg?.update()
    })

    let checkToast = { name: 'update toast appears with a Refresh action' }
    try {
      const toastText = page.locator('text=/A new version of Gameplan is available/i')
      await toastText.waitFor({ state: 'visible', timeout: 30000 })
      const refreshBtn = page.getByRole('button', { name: 'Refresh' })
      const refreshVisible = await refreshBtn.isVisible().catch(() => false)

      checkToast.toastVisible = true
      checkToast.refreshVisible = refreshVisible
      checkToast.screenshot = await shot(page, 'us8-update-toast')
      checkToast.pass = refreshVisible
      checkToast.symptom = refreshVisible
        ? 'toast shown with visible Refresh action'
        : 'toast text found but no visible "Refresh" button'
    } catch (e) {
      checkToast.pass = false
      checkToast.symptom = `threw/timed out: ${e.message}`
      checkToast.screenshot = await shot(page, 'us8-update-toast-missing')
    }
    result.checks.push(checkToast)

    if (checkToast.pass) {
      // --- Click Refresh: should postMessage SKIP_WAITING, the new worker activates,
      // fires `controllerchange`, and offline.ts's watchForControllerChange reloads the
      // page exactly once (guarded by a once-flag against a reload loop). ---
      let loadCount = 0
      page.on('load', () => {
        loadCount += 1
      })

      let checkRefresh = {
        name: `clicking Refresh reloads exactly once and ${TO_VERSION} takes control`,
      }
      try {
        // Wait for the actual reload's `load` event (deterministic) rather than a fixed
        // sleep — the click -> postMessage -> activate -> controllerchange -> reload
        // chain has no fixed duration, so a blind timeout is either flaky (too short) or
        // slow (too generous). Race the click against the reload so a `load` that fires
        // mid-click isn't missed.
        await Promise.all([
          page.waitForEvent('load', { timeout: 15000 }),
          page.getByRole('button', { name: 'Refresh' }).click({ timeout: 8000 }),
        ])
        // Let the reloaded page's own JS (offline.ts re-registering, SW settling) finish
        // booting before reading its state.
        await page.waitForTimeout(1500)

        const afterController = await page.evaluate(() => ({
          scriptURL: navigator.serviceWorker.controller?.scriptURL ?? null,
          state: navigator.serviceWorker.controller?.state ?? null,
        }))
        const afterCaches = await page.evaluate(() => caches.keys())

        checkRefresh.loadCount = loadCount
        checkRefresh.afterController = afterController
        checkRefresh.afterCaches = afterCaches
        const controllerActivated = afterController.state === 'activated'
        const newCachesPresent = afterCaches.some((n) => n.includes(`:${TO_VERSION}:`))
        const oldCachesGone = !afterCaches.some((n) => n.includes(`:${FROM_VERSION}:`))
        // Exactly one reload from the Refresh click. `load` also already fired once for
        // this listener's own attachment point (the page we're on when we attach), so we
        // count loads strictly AFTER attaching — loadCount should be exactly 1.
        checkRefresh.pass =
          loadCount === 1 && controllerActivated && newCachesPresent && oldCachesGone
        checkRefresh.symptom = checkRefresh.pass
          ? `single reload (loadCount=1), ${TO_VERSION} worker activated and controlling, old ${FROM_VERSION} caches evicted`
          : `loadCount=${loadCount} (expected 1), controllerActivated=${controllerActivated}, newCachesPresent=${newCachesPresent}, oldCachesGone=${oldCachesGone} — caches=${JSON.stringify(afterCaches)}`
      } catch (e) {
        checkRefresh.pass = false
        checkRefresh.symptom = `threw: ${e.message}`
        checkRefresh.screenshot = await shot(page, 'us8-refresh-error')
      }
      result.checks.push(checkRefresh)
    }

    result.pass = result.checks.every((c) => c.pass !== false)
  } catch (e) {
    result.pass = false
    result.fatalError = String(e)
  } finally {
    result.consoleErrors = consoleErrors
    result.pageErrors = pageErrors
    await context.setOffline(false).catch(() => {})
    await browser.close()

    // Always restore the original version + rebuild, regardless of outcome, so the rest
    // of the suite (and the repo state for the eventual commit) is unaffected by this
    // story having run.
    if (bumped) {
      try {
        bumpVersion(TO_VERSION, FROM_VERSION)
        build()
        result.reverted = true
      } catch (e) {
        result.revertError = String(e)
        result.pass = false
      }
    }
  }

  writeResult('us8', result)
  return result
}

if (require.main === module) {
  run().then((r) => {
    console.log(JSON.stringify(r, null, 2))
    process.exit(r.pass ? 0 : 1)
  })
}

module.exports = { run }
