import { watch } from 'vue'

/**
 * Postpones a page's own URL rewrites while it does not own the URL.
 *
 * Pages keep rendering behind the settings overlay, where the URL belongs to /settings/*.
 * A canonicalising `router.replace()` issued then would either throw (the page's params
 * are gone from the URL) or navigate the app off the settings route, closing the dialog
 * the moment it opened. Dropping those writes instead is not safe either — the composer's
 * `?draft=` link to its server row is written exactly once, and losing it strands the
 * draft row.
 *
 * So: run the write now if the page owns the URL, otherwise queue it and run it as soon as
 * the page owns the URL again (i.e. when the overlay closes). Queued writes run in the
 * order they were made and read their state when they run, so each one is postponed, not
 * frozen — pass a closure that re-reads, not pre-computed params.
 *
 * Must be called during setup: the watcher is disposed with the owning component, so a
 * page the user navigated away from simply drops whatever it had queued.
 *
 * @param ownsRoute Whether the current URL is one this page may rewrite.
 * @returns `runWhenOwned(write)` — run `write` now, or when the page owns the URL again.
 */
export function useOwnedRouteWrites(ownsRoute: () => boolean) {
  const pending: Array<() => void> = []

  watch(ownsRoute, (owned) => {
    if (!owned || pending.length === 0) return
    for (const write of pending.splice(0)) write()
  })

  return function runWhenOwned(write: () => void) {
    if (ownsRoute()) {
      write()
      return
    }
    pending.push(write)
  }
}
