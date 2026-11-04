const OFFLINE = { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 }
const ONLINE = { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }

declare global {
  namespace Cypress {
    interface Chainable {
      goOffline(): Chainable<void>
      goOnline(): Chainable<void>
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

export {}
