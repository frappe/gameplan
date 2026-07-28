// Live activity updates: a discussion you have open keeps up with what other
// people do to it, without a reload.
//
// The client contract has three parts, and this spec pins all three:
//   1. opening a discussion joins that document's realtime room,
//   2. a `new_activity` event for it refreshes the timeline in place,
//   3. leaving the discussion leaves the room again.
//
// The change itself is made by a *real* second session (`member`, via the
// `requestAsUser` Node task) while the browser stays logged in as `member2` and
// never reloads — so the timeline entry that shows up can only have come from
// genuine delivery through the document room, not from the acting user's own save.
import { resetData } from '../../support/seed'

type AppSocket = {
  emit: (...args: unknown[]) => unknown
}

/**
 * The app's socket.io client, as wired up in `src/main.js`
 * (`app.config.globalProperties.$socket`).
 */
function appSocket(): Cypress.Chainable<AppSocket> {
  return cy
    .window({ log: false })
    .its('document')
    .then((doc) => {
      const app = (doc.querySelector('#app') as { __vue_app__?: any } | null)?.__vue_app__
      const socket = app?.config?.globalProperties?.$socket
      expect(socket, 'app socket').to.exist
      return socket as AppSocket
    })
}

describe('Realtime activity', () => {
  let community: string
  let space: string
  let discussion: string

  beforeEach(function () {
    // Check the exact sites before resetData can wipe anything. The second call,
    // after seeding, also proves fresh sessions resolve as the watching persona on
    // both the browser server and Socket.IO's :8000 authentication target.
    cy.task<RealtimePreflightResult>('realtimePreflight').then((preflight) => {
      if (!preflight.available) {
        cy.log(preflight.reason ?? 'Realtime E2E capability unavailable')
        this.skip()
      }
    })
    resetData('space_with_discussion').then((ids) => {
      community = ids.community as string
      space = ids.space as string
      discussion = ids.discussion as string
    })
    cy.task('realtimePreflight', { user: 'member2@example.com' })
    cy.loginAs('secondMember')
  })

  it("shows another member's change in an open discussion without a reload", () => {
    // Land on the space first so the socket exists before the discussion mounts:
    // the subscribe happens on mount, and a spy installed afterwards would miss it.
    cy.intercept('GET', '/api/v2/document/GP%20Activity*').as('getActivities')
    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    appSocket().then((socket) => {
      cy.spy(socket, 'emit').as('socketEmit')
    })

    cy.contains('Welcome thread').click()
    cy.contains('h1', 'Welcome thread').should('be.visible')
    cy.wait('@getActivities')

    cy.get('@socketEmit').should(
      'have.been.calledWith',
      'doc_subscribe',
      'GP Discussion',
      String(discussion),
    )

    // `member` closes the discussion from a session of their own. The browser is
    // untouched: no reload, no navigation, still logged in as `member2`.
    cy.task('requestAsUser', {
      user: 'member@example.com',
      path: `/api/v2/document/GP Discussion/${discussion}/method/close_discussion`,
    })

    // The only reload after the initial fetch is initiated by CommentsArea's
    // `new_activity` listener. There is no navigation or browser reload.
    cy.wait('@getActivities')
    cy.contains('closed this discussion').should('be.visible')

    // Leaving the discussion leaves its room, so a tab that has moved on stops
    // being told about it.
    cy.go('back')
    cy.contains('h1', 'Welcome thread').should('not.exist')
    cy.get('@socketEmit').should(
      'have.been.calledWith',
      'doc_unsubscribe',
      'GP Discussion',
      String(discussion),
    )
  })
})

interface RealtimePreflightResult {
  available: boolean
  reason?: string
}
