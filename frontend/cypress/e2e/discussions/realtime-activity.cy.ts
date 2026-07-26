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
// the socket event, not from the acting user's own save.
//
// What is simulated: the delivery hop, and only that. See `deliverSocketEvent`.
import { resetData } from '../../support/seed'

type AppSocket = {
  nsp: string
  emit: (...args: unknown[]) => unknown
  io: { engine: { emit: (event: string, data: string) => void } }
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

/**
 * Deliver a server event to the page's socket.
 *
 * The frame is handed to the engine, so the real socket.io decoder, namespace
 * routing and listener dispatch all run — only the network hop is skipped.
 *
 * It has to be skipped on a local bench: the realtime server authenticates every
 * socket by calling the site named by `webserver_port` in `common_site_config.json`
 * (`apps/frappe/realtime/utils.js::get_url` under `developer_mode`), which is a
 * different site than the one Cypress drives. The session is unknown there, so the
 * tab connects as Guest and is refused the document room. That is a bench-layout
 * problem, not a Gameplan one — the server half (the event goes to the *document*
 * room, addressed and shaped exactly as below) is pinned in
 * `gameplan/tests/features/test_realtime_activity.py`.
 */
function deliverSocketEvent(event: string, payload: unknown) {
  appSocket().then((socket) => {
    socket.io.engine.emit('data', `2${socket.nsp},${JSON.stringify([event, payload])}`)
  })
}

describe('Realtime activity', () => {
  let community: string
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = ids.community as string
      space = ids.space as string
      discussion = ids.discussion as string
    })
    cy.loginAs('secondMember')
  })

  it("shows another member's change in an open discussion without a reload", () => {
    // Land on the space first so the socket exists before the discussion mounts:
    // the subscribe happens on mount, and a spy installed afterwards would miss it.
    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    appSocket().then((socket) => {
      cy.spy(socket, 'emit').as('socketEmit')
    })

    cy.contains('Welcome thread').click()
    cy.contains('h1', 'Welcome thread').should('be.visible')

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
    // Nothing tells this tab about it yet, so the timeline that shows the close
    // below can only have come from the event.
    cy.contains('closed this discussion').should('not.exist')

    deliverSocketEvent('new_activity', {
      reference_doctype: 'GP Discussion',
      reference_name: String(discussion),
    })

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
