import type { RouteLocationNormalized } from 'vue-router'
import router, { getHomeRoute } from '@/router'
import { useIsMobile } from '@/utils/useIsMobile'

/**
 * Browser history for the desktop settings dialog.
 *
 * The dialog is a layer over a page, so history stays page-shaped: an open dialog sits
 * in one entry above that page (two when a community is open, so Back returns to the
 * list). Closing steps back to the page instead of pushing it again, and a link out of
 * the dialog does the same first. The dialog then stays out of the way of Back.
 *
 * Each settings entry records the page beneath it in history.state, which is what lets
 * reload, Back and Forward find that page again. Phones keep plain history: settings
 * there is an ordinary page, and its entries carry no record.
 */
interface OverlayBase {
  path: string
  /** vue-router's history position of the page's entry. */
  position: number
}

const BASE_KEY = 'settingsOverlayBase'
const isPhone = useIsMobile()
let currentBase: OverlayBase | null = null

export function isSettingsRoute(route: RouteLocationNormalized) {
  return route.matched.some((record) => record.meta?.settingsOverlay)
}

/** Finds the page beneath the settings route being entered. Null: moving within settings. */
export function resolveOverlayBase(to: RouteLocationNormalized, from: RouteLocationNormalized) {
  currentBase = readBase() ?? newBase(to, from)
  return currentBase
}

/** Runs once `to` is committed, because each new entry starts with a blank state. */
export function recordOverlayBase() {
  if (isPhone.value || !currentBase) return
  window.history.replaceState({ ...window.history.state, [BASE_KEY]: currentBase }, '')
}

/** True for a new navigation from settings to a page. Back and Forward land on an entry with no record. */
export function isLeavingOverlay(to: RouteLocationNormalized, from: RouteLocationNormalized) {
  return isSettingsRoute(from) && !isSettingsRoute(to) && stepsToBase() > 0
}

export function closeSettings() {
  const steps = stepsToBase()
  if (steps > 0) {
    router.go(-steps)
    return
  }
  // No page below to return to: a phone-sized window was widened, or the entry was
  // replaced by a redirect (?settings=notifications). Clear the record with the entry.
  router.replace({ path: router.resolve(getHomeRoute()).path, state: { [BASE_KEY]: null } })
}

/** Removes the dialog's entries, then opens `to`, so Back from `to` skips the dialog. */
export function leaveOverlayFor(to: RouteLocationNormalized) {
  if (readBase()?.path !== to.fullPath) {
    window.addEventListener('popstate', () => router.push(to.fullPath), { once: true })
  }
  closeSettings()
}

function stepsToBase() {
  const base = readBase()
  return base ? window.history.state.position - base.position : 0
}

function readBase(): OverlayBase | null {
  return window.history.state?.[BASE_KEY] ?? null
}

function newBase(to: RouteLocationNormalized, from: RouteLocationNormalized): OverlayBase | null {
  if (isSettingsRoute(from)) return null
  const position: number = window.history.state.position
  if (from.matched.length > 0) return { path: from.fullPath, position }
  return coldLoadBase(to, position)
}

/**
 * A cold load has no page below the dialog, so put Home there. Close and Back then work
 * as they do everywhere else, and no entry is left that reopens the dialog.
 */
function coldLoadBase(to: RouteLocationNormalized, position: number): OverlayBase {
  const path = router.resolve(getHomeRoute()).fullPath
  if (!isPhone.value) {
    router.options.history.replace(path)
    router.options.history.push(to.fullPath)
  }
  return { path, position }
}
