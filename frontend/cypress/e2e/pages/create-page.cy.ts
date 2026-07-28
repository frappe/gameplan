import { resetData } from '../../support/seed'

describe('Pages in a space', () => {
  let community: string
  let space: string

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
    })
    cy.loginAs('member')
  })

  it('creates a page, edits its content, and keeps the edit after reload', () => {
    cy.visit(`/g/community/${community}/space/${space}/pages`)
    cy.intercept('POST', '/api/v2/document/GP%20Page').as('createPage')
    cy.button('Add new').click()
    cy.wait('@createPage')

    // A new page opens straight into the editor with a placeholder title.
    cy.url().should('include', `/g/community/${community}/space/${space}/pages/`)
    cy.get('input[placeholder="Title"]').should('have.value', 'Untitled')

    cy.intercept('PUT', '/api/v2/document/GP%20Page/*').as('savePage')
    const pageContent = 'This handbook edit must survive a reload.'
    cy.get('[contenteditable=true]').should('be.visible').click().type(pageContent)
    cy.wait('@savePage').its('response.body.data.content').should('contain', pageContent)

    cy.reload()
    cy.get('[contenteditable=true]').should('be.visible').should('contain.text', pageContent)

    // The breadcrumb walks back to the space's pages tab, which now lists it.
    cy.get('header').contains('a', 'Pages').click()
    cy.url().should(
      'eq',
      `${Cypress.config().baseUrl}/g/community/${community}/space/${space}/pages`,
    )
    cy.contains('a', 'Untitled').should('exist')
  })
})
