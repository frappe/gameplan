import { resetData } from '../../support/seed'

// The scoped new-space flow always creates in the current community (no community
// picker), and the legacy /spaces route sends everyone back to their community.
// Community management shortcuts stay hidden from plain members.
describe('Space creation guardrails', () => {
  let community: string

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
    })
  })

  it('creates a space in the current community from the sidebar', () => {
    cy.loginAs('admin')
    cy.visit(`/g/community/${community}/discussions`)

    // The sidebar "Spaces" header carries a "+" (aria-label "New space").
    cy.iconButton('New space').click()

    // The dialog opens in locked mode: title shown, community picker hidden.
    cy.scope('dialog').contains('New Space').should('be.visible')
    cy.get('input[placeholder="Community"]').should('not.exist')

    cy.scope('dialog').find('#new-space-name').type('Platform')
    cy.scope('dialog').button('Submit').click()

    // Dialog closes and the new space lands in the current community's sidebar.
    cy.scope('dialog').should('not.exist')
    cy.contains('a', 'Platform')
      .should('have.attr', 'href')
      .and('include', `/community/${community}/space/`)
  })

  it('sends a plain member from /spaces back to their community', () => {
    cy.loginAs('member')
    cy.visit('/g/spaces')

    cy.url().should('not.include', '/spaces')
    cy.url().should('include', `/community/${community}/discussions`)

    // The rail's community management shortcut is admin-only.
    cy.get('button[aria-label="Configure communities"]').should('not.exist')
  })
})
