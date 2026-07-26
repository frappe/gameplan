import { resetData } from '../../support/seed'

describe('Mobile discussion creation', () => {
  let community: string
  let space: string

  beforeEach(() => {
    cy.viewport('iphone-6')
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
    })
    cy.loginAs('member')
  })

  it('creates a discussion and posts a comment', () => {
    cy.intercept(
      'POST',
      '/api/method/gameplan.gameplan.doctype.gp_draft.gp_draft.publish_draft',
    ).as('publishDiscussion')

    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    cy.get('[aria-label="New discussion"]').should('be.visible').click()

    cy.get('div[contenteditable=true]')
      .should('be.visible')
      .click()
      .type('A discussion created from a phone.')
    cy.get('textarea[placeholder="Title"]')
      .should('be.visible')
      .type('Mobile discussion')
      .should('have.value', 'Mobile discussion')
    cy.button('Publish').click()

    cy.wait('@publishDiscussion')
      .its('response.body.message')
      .then((discussion: string) => {
        cy.url().should(
          'include',
          `/g/community/${community}/space/${space}/discussion/${discussion}/mobile-discussion`,
        )
      })
    cy.contains('h1', 'Mobile discussion').should('be.visible')

    cy.intercept('POST', '/api/v2/document/GP%20Comment').as('postComment')
    cy.button('Add a comment').click()
    cy.get('[contenteditable=true]')
      .should('be.visible')
      .click()
      .type('A comment posted from a phone.')
    cy.button('Submit').click()

    cy.wait('@postComment')
      .its('response.body.data')
      .then((comment: { name: string }) => {
        cy.get(`div[data-id="${comment.name}"]`)
          .should('be.visible')
          .and('contain.text', 'A comment posted from a phone.')
      })
  })
})
