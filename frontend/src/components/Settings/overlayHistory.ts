import type { RouteLocationNormalized, RouteLocationRaw } from 'vue-router'
import router, { getHomeRoute } from '@/router'
import { useIsMobile } from '@/utils/useIsMobile'

/*
 * Browser history for the desktop settings dialog.
 *
 * The dialog is a layer over a page, so an open dialog sits in one history entry above
 * that page (two when a community is open, so Back returns to the list). Closing steps
 * back to the page instead of pushing it again, and a link out of the dialog does the
 * same first, so Back from anywhere skips the dialog.
 *
 * Each settings entry records the page beneath it in history.state. Closing after a
 * reload, Back or Forward reads that record to find the page again. Phones keep plain history: settings
 * is an ordinary page there, and its entries carry no record.
 */

interface OverlayBase {
  path: string
  /** vue-router's history position of the page's entry. */
  position: number
}

/** The fields this module reads from history.state, which the DOM types as `any`. */
interface EntryState {
  position: number
  back: string | null
  settingsOverlayBase?: OverlayBase | null
}

const isPhone = useIsMobile()
let currentBase: OverlayBase | null = null

export function isSettingsRoute(route: Pick<RouteLocationNormalized, 'matched'>) {
  return route.matched.some((record) => record.meta?.settingsOverlay)
}

/**
 * Finds the page beneath the settings route being entered, adding it to history on a
 * cold load. Null when moving within settings with no record, as on a phone.
 */
export function resolveOverlayBase(to: RouteLocationNormalized, from: RouteLocationNormalized) {
  currentBase = readBase() ?? newBase(to, from)
  return currentBase
}

/** Runs once `to` is committed, because each new entry starts with a blank state. */
export function recordOverlayBase() {
  if (isPhone.value || !currentBase) return
  window.history.replaceState({ ...entryState(), settingsOverlayBase: currentBase }, '')
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
  router.replace({ path: homePath(), state: { settingsOverlayBase: null } })
}

/**
 * Returns to `to` when it is the entry directly below, so moving in and out of a
 * sub-screen does not stack entries. Phones keep plain history.
 */
export function returnToSettingsEntry(to: RouteLocationRaw) {
  const target = router.resolve(to)
  if (isPhone.value) router.push(target)
  else if (entryState().back === target.fullPath) router.back()
  else router.replace(target)
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
  return base ? entryState().position - base.position : 0
}

function readBase(): OverlayBase | null {
  return entryState().settingsOverlayBase ?? null
}

function newBase(to: RouteLocationNormalized, from: RouteLocationNormalized): OverlayBase | null {
  if (isSettingsRoute(from)) return null
  const { position } = entryState()
  if (from.matched.length > 0) return { path: from.fullPath, position }
  return coldLoadBase(to, position)
}

/**
 * A cold load has no page below the dialog, so put Home there. Close and Back then work
 * as they do everywhere else, and no entry is left that reopens the dialog.
 */
function coldLoadBase(to: RouteLocationNormalized, position: number): OverlayBase {
  const path = homePath()
  if (!isPhone.value) {
    router.options.history.replace(path)
    router.options.history.push(to.fullPath)
  }
  return { path, position }
}

function homePath() {
  return router.resolve(getHomeRoute()).fullPath
}

function entryState(): EntryState {
  return window.history.state
}
