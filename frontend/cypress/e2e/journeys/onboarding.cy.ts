// Onboarding creates a Community + a first Space. The GP Team after_insert hook
// also auto-creates a public `General` space, so a freshly onboarded site lands
// with two spaces, scoped to the new community's discussions.
//
// Seeds nothing: an empty Gameplan is what puts a user on the onboarding wizard.
import { resetData } from '../../support/seed'

describe('Onboarding', () => {
  beforeEach(() => {
    resetData()
    cy.loginAs('admin')
  })

  it('creates a community + first space and lands on community discussions', () => {
    cy.visit('/g')
    cy.url().should('include', '/onboarding')

    cy.get('input#new-community-name').type('Acme')
    cy.get('input[placeholder*=Townhall]').type('Marketing')
    cy.button('Continue').click()

    // Lands on the new community's canonical discussions URL.
    cy.url().should('match', /\/community\/[^/]+\/discussions/)

    // Page tabs show the discussions feed, and the sidebar lists the auto-created
    // public General space plus the user-named space.
    cy.contains('All Discussions').should('exist')
    cy.contains('a', 'General').should('exist')
    cy.contains('a', 'Marketing').should('exist')
  })
})
