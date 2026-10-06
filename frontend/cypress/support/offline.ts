/**
 * Offline support for the e2e suite.
 *
 * The app decides it is offline from `navigator.onLine` and the `online`/`offline` events
 * (vueuse's `useNetwork`, read once in `data/online.ts`), and its request gate rejects
 * `/api/` while that says offline (`data/offline/requests.ts`). These commands drive the
 * browser itself through CDP so both of those see the real thing, rather than stubbing the
 * flag and hoping the rest follows.
 */

const OFFLINE = { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 }
const ONLINE = { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }

/** idb-keyval's default store, which every frappe-ui resource caches into. */
export const RESOURCE_STORE = { db: 'keyval-store', store: 'keyval' } as const
/** draftStore.ts keeps its own, so drafts survive a logout that clears the rest. */
export const DRAFT_STORE = { db: 'gameplan-drafts', store: 'records' } as const

export const LAST_SEEN_USER_KEY = 'gameplan:last-seen-user'

/** The prefix frappe-ui puts on every cache key it writes for a signed-in user. */
export function cacheNamespace(email: string) {
  return `ns:${encodeURIComponent(email)}:`
}
/** gameplan-sw.js names its buckets `gameplan-readonly-offline:<version>:<kind>`. */
export const CACHE_PREFIX = 'gameplan-readonly-offline'

interface IdbStore {
  db: string
  store: string
}

declare global {
  namespace Cypress {
    interface Chainable {
      /** Cut the browser off the network, as the Network panel's Offline preset does. */
      goOffline(): Chainable<void>
      goOnline(): Chainable<void>
      /**
       * The keys held in one IndexedDB store, or `[]` where the database or store has
       * never been created. Both stores are read the same way, so they share this.
       */
      idbKeys(store?: IdbStore): Chainable<string[]>
      /** Cache Storage bucket names, or `[]` where the worker never ran. */
      cacheNames(): Chainable<string[]>
      /** Whether a service worker controls the page — false on an insecure origin. */
      serviceWorkerActive(): Chainable<boolean>
      /** The account this browser last saw, which is how a user switch is detected. */
      lastSeenUser(): Chainable<string | null>
    }
  }
}

function emulate(conditions: typeof OFFLINE) {
  return Cypress.automation('remote:debugger:protocol', {
    command: 'Network.emulateNetworkConditions',
    params: conditions,
  })
}

/**
 * `navigator.onLine` is what the app watches, and Chrome updates it from the emulation —
 * but not always before the next command runs, so the change is awaited rather than
 * assumed. The events are dispatched only if Chrome has not already fired them, which is
 * what `onLine` flipping tells us.
 */
function setOffline(offline: boolean) {
  cy.wrap(null, { log: false })
    .then(() => Cypress.automation('remote:debugger:protocol', { command: 'Network.enable' }))
    .then(() => emulate(offline ? OFFLINE : ONLINE))
  cy.window({ log: false }).its('navigator.onLine', { timeout: 10000 }).should('eq', !offline)
}

Cypress.Commands.add('goOffline', () => setOffline(true))
Cypress.Commands.add('goOnline', () => setOffline(false))

// A test that ends or fails offline must not leave the next one, or the report, offline.
beforeEach(() => cy.goOnline())
afterEach(() => cy.goOnline())

Cypress.Commands.add('idbKeys', (store: IdbStore = RESOURCE_STORE) =>
  cy.window({ log: false }).then(
    (win) =>
      new Cypress.Promise<string[]>((resolve) => {
        const request = win.indexedDB.open(store.db)
        request.onerror = () => resolve([])
        request.onsuccess = () => {
          const db = request.result
          if (!db.objectStoreNames.contains(store.store)) {
            db.close()
            resolve([])
            return
          }
          const keys = db.transaction(store.store, 'readonly').objectStore(store.store).getAllKeys()
          const done = (value: string[]) => {
            db.close()
            resolve(value)
          }
          keys.onsuccess = () => done(keys.result as string[])
          keys.onerror = () => done([])
        }
      }),
  ),
)

Cypress.Commands.add('cacheNames', () =>
  cy
    .window({ log: false })
    .then((win) =>
      win.caches
        ? new Cypress.Promise<string[]>((resolve) =>
            win.caches.keys().then(resolve, () => resolve([])),
          )
        : new Cypress.Promise<string[]>((resolve) => resolve([])),
    ),
)

Cypress.Commands.add('serviceWorkerActive', () =>
  cy.window({ log: false }).then((win) => Boolean(win.navigator.serviceWorker?.controller)),
)

Cypress.Commands.add('lastSeenUser', () =>
  cy.window({ log: false }).then((win) => {
    try {
      return win.localStorage.getItem(LAST_SEEN_USER_KEY)
    } catch {
      return null
    }
  }),
)

/**
 * Whether this run can exercise the service worker at all.
 *
 * A worker only registers in a secure context, which over http means `localhost` or a
 * loopback literal — `gameplan.test` is not one. Specs that need the worker say so through
 * this rather than failing with something that looks like a product bug.
 */
export function secureOrigin() {
  const base = Cypress.config('baseUrl') || ''
  return /^https:/.test(base) || /\/\/(localhost|127\.0\.0\.1|\[::1\])(:|\/|$)/.test(base)
}

export {}
