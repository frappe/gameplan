// Writing offline: the controls that need the server are disabled rather than broken, what
// was typed is kept, and it posts once the connection is back.
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

  it('refuses a reaction offline and takes it once back', () => {
    cy.goOffline()
    // Reactions are refused outright offline rather than queued, so nothing is posted
    // later that the person cannot see they sent.
    cy.get('button[aria-label="Add a reaction"]').first().should('be.disabled')

    cy.goOnline()
    cy.get('button[aria-label="Add a reaction"]').first().should('not.be.disabled')
  })
})
