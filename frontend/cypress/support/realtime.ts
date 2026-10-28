// Helpers for specs that exercise the app's live socket.io connection.
import type { App } from 'vue'
import type { Socket } from 'socket.io-client'

interface RealtimePreflightResult {
  available: boolean
  reason?: string
}

/**
 * Skip the current test when this bench cannot deliver realtime events (no socket server,
 * or sites that resolve differently for it). Call from `beforeEach(function () {...})`.
 */
export function skipUnlessRealtime(context: Mocha.Context) {
  cy.task<RealtimePreflightResult>('realtimePreflight').then((preflight) => {
    if (!preflight.available) {
      cy.log(preflight.reason ?? 'Realtime E2E capability unavailable')
      context.skip()
    }
  })
}

/**
 * The app's socket.io client, as wired up in `src/main.ts`
 * (`app.config.globalProperties.$socket`).
 */
export function appSocket(): Cypress.Chainable<Socket> {
  return cy
    .window({ log: false })
    .its('document')
    .then((doc) => {
      const app = (doc.querySelector('#app') as { __vue_app__?: App } | null)?.__vue_app__
      const socket = app?.config.globalProperties.$socket as Socket | undefined
      expect(socket, 'app socket').to.exist
      return socket!
    })
}
