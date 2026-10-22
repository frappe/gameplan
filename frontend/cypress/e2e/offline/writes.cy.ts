// Writing offline: sending a comment or a reaction says it needs the connection, and what
// was typed stays until it's back.
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
    cy.intercept('GET', '**/api/v2/document/GP%20Comment?*').as('comments')

    cy.button('Add a comment').click()
    composer().click().type('written while the connection was gone')

    cy.goOffline()
    cy.button('Submit').click()
    cy.contains("You're offline. Reconnect to do this.").should('be.visible')
    cy.get('@postComment.all').should('have.length', 0)
    composer().should('contain.text', 'written while the connection was gone')

    cy.goOnline()
    // Reconnecting reloads the comments, which redraws the composer; click after that.
    cy.wait('@comments')
    cy.button('Submit').click()
    cy.wait('@postComment').its('response.statusCode').should('eq', 200)
    cy.contains('written while the connection was gone').should('be.visible')
  })

  it('says a reaction needs the connection', () => {
    cy.intercept('POST', '**/api/v2/document/GP%20Discussion/*/method/react').as('react')
    cy.goOffline()
    cy.get('button[aria-label="Add a reaction"]').first().click()
    cy.get('button:contains("👍"):visible').click()
    cy.contains("You're offline. Reconnect to do this.").should('be.visible')
    cy.contains('button', /👍\s*1/).should('not.exist')
    cy.get('@react.all').should('have.length', 0)
  })
})
