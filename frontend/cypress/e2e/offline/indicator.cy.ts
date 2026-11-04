// Knowing you are offline: the banner appears when the connection drops and goes when it
// returns, and a write refused because of it says so.
//
// The banner is matched by its role and exact text rather than anything containing
// "offline" — the seeded personas and spaces can carry that word themselves.
import { resetData } from '../../support/seed'

describe('Offline indicator', () => {
  let spacePath: string

  beforeEach(() => {
    resetData('space_with_discussion').then(({ community, space, discussion, discussion_slug }) => {
      spacePath = `/g/community/${community}/space/${space}/discussions`
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

  it('says so when a write is refused', () => {
    cy.goOffline()
    banner().should('be.visible')
    cy.selectDropdownOption('Discussion Options', 'Bookmark')
    cy.contains("You're offline. Reconnect to do this.").should('be.visible')
  })

  it('stays quiet when a saved page is opened', () => {
    // Opening a discussion reads over POST (find_my_draft) and writes a visit on its own;
    // neither is something the person asked for.
    cy.then(() => cy.visit(spacePath))
    cy.contains('a', 'Welcome thread').should('be.visible')
    cy.goOffline()
    cy.contains('a', 'Welcome thread').click()
    cy.contains('h1', 'Welcome thread').should('be.visible')
    // Long enough for a wrongly shown toast to appear.
    cy.wait(2000)
    cy.contains("You're offline. Reconnect to do this.").should('not.exist')
  })
})
