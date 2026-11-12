// Helpers for specs that exercise the app's live socket.io connection.
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
 * The app's socket.io client, which `src/socket.ts` exposes as `window.gameplanSocket` while
 * Cypress drives the app. It connects after the first page draws, so this waits for it.
 */
export function appSocket(): Cypress.Chainable<Socket> {
  return cy
    .window({ log: false })
    .its('gameplanSocket', { log: false })
    .then((socket) => socket as Socket)
}
