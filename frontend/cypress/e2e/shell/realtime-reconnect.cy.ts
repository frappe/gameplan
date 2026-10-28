// Unread counts after a dropped connection: a post made while the socket was down is never
// pushed, so the app has to ask for fresh counts when the socket comes back.
//
// The post is made by a *real* second session (`member`, via the `requestAsUser` Node task)
// while the browser stays logged in as `member2` and never reloads. Reconnection is paused
// until the post is saved, so its realtime push is lost for certain, and the badge can only
// update through the refetch that runs on reconnect.
import type { Socket } from 'socket.io-client'
import { resetData } from '../../support/seed'

/**
 * socket.io's Manager keeps the switch that resumes reconnection private. The test reaches
 * for it so the socket stays down exactly as long as the post takes, with no timing guess.
 */
type ResumableManager = Socket['io'] & {
  skipReconnect: boolean
  reconnect: () => void
}

/**
 * The app's socket.io client, as wired up in `src/main.js`
 * (`app.config.globalProperties.$socket`).
 */
function appSocket(): Cypress.Chainable<Socket> {
  return cy
    .window({ log: false })
    .its('document')
    .then((doc) => {
      const app = (doc.querySelector('#app') as { __vue_app__?: any } | null)?.__vue_app__
      const socket = app?.config?.globalProperties?.$socket
      expect(socket, 'app socket').to.exist
      return socket as Socket
    })
}

describe('Realtime reconnect', () => {
  let community: string
  let space: string

  beforeEach(function () {
    cy.task<RealtimePreflightResult>('realtimePreflight').then((preflight) => {
      if (!preflight.available) {
        cy.log(preflight.reason ?? 'Realtime E2E capability unavailable')
        this.skip()
      }
    })
    // Seeds "Welcome thread" by `member`, so it starts unread for `member2`.
    resetData('space_with_discussion').then((ids) => {
      community = ids.community as string
      space = ids.space as string
    })
    cy.task('realtimePreflight', { user: 'member2@example.com' })
    cy.loginAs('secondMember')
  })

  it('catches up on unread counts missed while the socket was down', () => {
    cy.visit(`/g/community/${community}/discussions`)
    cy.get('button[aria-label="Acme, 1 unread"]:visible').should('exist')
    appSocket().its('connected').should('eq', true)

    appSocket().then((socket) => {
      socket.io.reconnection(false)
      socket.io.engine.close()
    })
    appSocket().its('connected').should('eq', false)

    cy.task('requestAsUser', {
      user: 'member@example.com',
      path: '/api/v2/document/GP Discussion',
      body: { title: 'Posted while offline', project: space, content: '<p>Hello</p>' },
    })

    appSocket().then((socket) => {
      const manager = socket.io as ResumableManager
      manager.reconnection(true)
      manager.skipReconnect = false
      manager.reconnect()
    })
    appSocket().its('connected').should('eq', true)

    cy.get('button[aria-label="Acme, 2 unread"]:visible').should('exist')
  })
})

interface RealtimePreflightResult {
  available: boolean
  reason?: string
}
