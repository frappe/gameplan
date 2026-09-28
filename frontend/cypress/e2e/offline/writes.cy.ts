// Writing offline: the composer waits for the connection and keeps what was typed, and
// reacting waits for it too.
import { resetData } from '../../support/seed'

describe('Writing while offline', () => {
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
    // Deferred: the ids above are only set once the seed has answered.
    cy.then(() =>
      cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`),
    )
    cy.contains('h1', 'Welcome thread').should('be.visible')
  })

  const composer = () => cy.get('.ProseMirror').last()

  it('keeps a reply typed offline and posts it on reconnect', () => {
    cy.intercept('POST', '**/api/v2/document/GP%20Comment').as('postComment')

    cy.button('Add a comment').click()
    composer().click().type('written while the connection was gone')

    cy.goOffline()
    // Still on screen, and the way to send it is shut rather than silently failing.
    composer().should('contain.text', 'written while the connection was gone')
    cy.button('Submit').should('be.disabled')

    cy.goOnline()
    cy.button('Submit').should('not.be.disabled').click()
    cy.wait('@postComment').its('response.statusCode').should('eq', 200)
    cy.contains('written while the connection was gone').should('be.visible')
  })

  it('disables reacting until the connection is back', () => {
    const addReaction = () => cy.get('button[aria-label="Add a reaction"]').first()
    addReaction().should('be.enabled')
    cy.goOffline()
    addReaction().should('be.disabled')
    cy.goOnline()
    addReaction().should('be.enabled')
  })
})
