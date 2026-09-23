// Reading offline: what was opened while online opens again without a connection, and
// what was never opened says so plainly instead of rendering as empty.
//
// Navigation here is in-app rather than by reload: a reload needs the service worker to
// serve the shell, which app-shell.cy.ts covers on its own.
import { resetData } from '../../support/seed'

describe('Reading offline', () => {
  let community: string
  let space: string
  let discussion: string
  let slug: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
      slug = String(ids.discussion_slug)
    })
    cy.loginAs('member')
  })

  const discussionPath = () =>
    `/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`

  it('renders a discussion that was opened online', () => {
    cy.visit(discussionPath())
    cy.contains('h1', 'Welcome thread').should('be.visible')

    // Back to the feed, offline, then in by the same link a reader would use.
    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    cy.contains('a', 'Welcome thread').should('be.visible')

    cy.goOffline()
    cy.contains('a', 'Welcome thread').click()
    cy.contains('h1', 'Welcome thread').should('be.visible')
    cy.url().should('include', `/discussion/${discussion}`)

    cy.goOnline()
  })

  it('says so when the content was never opened', () => {
    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    cy.get('[data-slot="desktop-shell"]').should('exist')

    cy.goOffline()
    // A space that has never been opened has nothing cached to render.
    cy.visit(`/g/community/${community}/space/${space}/pages`, { failOnStatusCode: false })
    cy.contains(/can't load|couldn't load/i).should('be.visible')
    cy.button('Retry').should('be.visible')

    cy.goOnline()
  })

  it('offers a retry on search, which runs itself once the connection returns', () => {
    cy.visit('/g/search')
    cy.get('input[type="search"], input[placeholder*="Search" i]').first().as('search')

    cy.goOffline()
    cy.get('@search').type('welcome{enter}')
    cy.contains('Search needs a connection').should('be.visible')
    cy.button('Retry').should('be.visible')

    // Reconnecting re-runs the query rather than leaving the reader to press Retry.
    cy.goOnline()
    cy.contains('Search needs a connection', { timeout: 20000 }).should('not.exist')
  })
})
