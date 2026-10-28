// A post made while the socket was down is never pushed, so the app has to ask for fresh
// unread counts when the socket comes back.
import { resetData } from '../../support/seed'
import { appSocket, skipUnlessRealtime } from '../../support/realtime'

describe('Realtime reconnect', () => {
  let community: string
  let space: string

  beforeEach(function () {
    skipUnlessRealtime(this)
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

    // `member` posts from a session of their own while this tab is offline, so the badge
    // can only change through the refetch that runs on reconnect.
    appSocket().invoke('disconnect')
    cy.task('requestAsUser', {
      user: 'member@example.com',
      path: '/api/v2/document/GP Discussion',
      body: { title: 'Posted while offline', project: space, content: '<p>Hello</p>' },
    })
    appSocket().invoke('connect')

    cy.get('button[aria-label="Acme, 2 unread"]:visible').should('exist')
  })
})
