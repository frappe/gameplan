import { resetData } from '../../support/seed'

// TipTap's default allowedPrefixes is only a space. frappe-ui 1.0.0-beta.61
// (frappe/frappe-ui#1129) also treats `( [ { <` and quotes as mention prefixes.
describe('Mention prefixes', () => {
  let community: string
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
    })
    cy.loginAs('member')
  })

  function visitDiscussion() {
    cy.intercept('GET', `/api/v2/document/GP%20Discussion/${discussion}`).as('getDiscussion')
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)
    cy.wait('@getDiscussion')
    cy.button('Add a comment').click()
    cy.get('[contenteditable=true]').should('be.visible').click()
  }

  it('opens the mention list after an opening parenthesis', () => {
    visitDiscussion()
    cy.get('[contenteditable=true]').type('(@')
    cy.get('[aria-label="Suggestions"]').should('be.visible')
    cy.get('[aria-label="Suggestions"]').contains('Everyone').should('be.visible')
  })

  it('does not open the mention list inside an email address', () => {
    visitDiscussion()
    cy.get('[contenteditable=true]').type('test@example.com')
    cy.get('[aria-label="Suggestions"]').should('not.exist')
  })

  it('inserts @ after ( from the toolbar without a padding space', () => {
    visitDiscussion()
    cy.get('[contenteditable=true]').type('(')
    cy.iconButton('Mention').click()
    cy.get('[contenteditable=true]').should('contain.text', '(@')
    cy.get('[contenteditable=true]').should('not.contain.text', '( @')
    cy.get('[aria-label="Suggestions"]').should('be.visible')
  })
})
