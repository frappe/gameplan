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

  it('creates a page from a space and returns to the pages tab', () => {
    cy.visit(`/g/community/${community}/space/${space}/pages`)
    cy.button('Add new').click()

    // A new page opens straight into the editor with a placeholder title.
    cy.url().should('include', `/g/community/${community}/space/${space}/pages/`)
    cy.get('input[placeholder="Title"]').should('have.value', 'Untitled')

    // The breadcrumb walks back to the space's pages tab, which now lists it.
    cy.get('header').contains('a', 'Pages').click()
    cy.url().should(
      'eq',
      `${Cypress.config().baseUrl}/g/community/${community}/space/${space}/pages`,
    )
    cy.contains('a', 'Untitled').should('exist')
  })
})
