// Knowing you are offline: the banner appears when the connection drops and goes when it
// returns, and a control that is disabled because of it says so when you tap it anyway.
//
// The banner is matched by its role and exact text rather than anything containing
// "offline" — the seeded personas and spaces can carry that word themselves.
import { resetData } from '../../support/seed'

describe('Offline indicator', () => {
  beforeEach(() => {
    resetData('space_with_discussion').then(({ community, space, discussion, discussion_slug }) => {
      cy.loginAs('member')
      cy.visit(
        `/g/community/${community}/space/${space}/discussion/${discussion}/${discussion_slug}`,
      )
    })
    cy.contains('h1', 'Welcome thread').should('be.visible')
  })

  const banner = () => cy.contains('[role="status"]', /^\s*Offline\s*$/)

  it('appears when the connection drops and clears when it returns', () => {
    banner().should('not.exist')

    cy.goOffline()
    banner().should('be.visible')
    // The shells are pushed down by exactly the banner's height, so it sits above the
    // header rather than over it (index.css keys off this attribute).
    cy.get('html').should('have.attr', 'data-offline')

    cy.goOnline()
    banner().should('not.exist')
    cy.get('html').should('not.have.attr', 'data-offline')
  })

  it('explains itself when a disabled control is tapped', () => {
    cy.get('button[aria-label="Add a reaction"]').should('exist')
    cy.goOffline()
    banner().should('be.visible')

    // Pointer events still reach a disabled control even though clicks do not, which is
    // what one listener in OfflineIndicator.vue uses to answer for every one of them.
    cy.get('button[aria-label="Add a reaction"]')
      .first()
      .should('be.disabled')
      .trigger('pointerup', { eventConstructor: 'PointerEvent', force: true })
    cy.contains("You're offline. Reconnect to do this.").should('be.visible')

    cy.goOnline()
  })
})
