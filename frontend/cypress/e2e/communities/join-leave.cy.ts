// Joining a community is what puts it and its public spaces in the sidebar. The
// Communities settings tab is where a member browses for one, so it is open to
// everyone and shows only the actions that user can take.
import { resetData } from '../../support/seed'

describe('Joining and leaving a community', () => {
  beforeEach(() => {
    resetData('two_communities')
    // The outsider persona belongs to no community, so every row starts on "Join".
    cy.loginAs('outsider')
  })

  const openCommunitiesSettings = () => {
    cy.visit('/g/settings/communities')
    cy.contains('h2:visible', 'Communities').should('be.visible')
  }

  const railItem = (title: string) => cy.get(`button[aria-label="${title}"]:visible`)

  it('joins a public community and lists it in the rail', () => {
    openCommunitiesSettings()
    railItem('Alpha').should('not.exist')

    cy.get('button[aria-label="Join Alpha"]:visible').click()

    cy.get('button[aria-label="Leave Alpha"]:visible').should('be.visible')
    railItem('Alpha').should('be.visible')
    // Joining one community leaves the others alone.
    cy.get('button[aria-label="Join Beta"]:visible').should('be.visible')
  })

  it('leaves after confirming and drops it from the rail', () => {
    openCommunitiesSettings()
    cy.get('button[aria-label="Join Alpha"]:visible').click()
    cy.get('button[aria-label="Leave Alpha"]:visible').click()

    cy.contains('[role="dialog"]', 'Leave "Alpha"?')
      .should('be.visible')
      .within(() => {
        cy.contains('button', 'Leave').click()
      })

    cy.get('button[aria-label="Join Alpha"]:visible').should('be.visible')
    railItem('Alpha').should('not.exist')
  })

  it('offers no community management to a member who manages none', () => {
    openCommunitiesSettings()

    cy.contains('button', 'New community').should('not.exist')
    cy.get('button[aria-label="Alpha Community Options"]').should('not.exist')
    // The image on a row is a plain avatar, not the admin's upload button.
    cy.get('button[aria-label="Upload image for Alpha"]').should('not.exist')
  })

  it('opens the customize sidebar dialog from the communities tab', () => {
    openCommunitiesSettings()

    cy.contains('button', 'Customize sidebar').click()
    cy.contains('[role="dialog"]', 'Shown in sidebar').should('be.visible')
  })

  it('offers no space management to a member who manages none', () => {
    cy.visit('/g/settings/communities/alpha/spaces')
    cy.contains('button:visible', 'Spaces').should('be.visible')

    cy.contains('button', 'New space').should('not.exist')
    cy.get('button[aria-label="Alpha Space Space Options"]').should('not.exist')
    // Renaming a space is a write on GP Project, which the backend refuses here.
    cy.get('input[aria-label="Space title"]:visible').first().should('be.disabled')
  })

  it('keeps the space management actions for an admin', () => {
    cy.loginAs('admin')
    cy.visit('/g/settings/communities/alpha/spaces')

    cy.contains('button:visible', 'New space').should('be.visible')
    cy.get('button[aria-label="Alpha Space Space Options"]:visible').should('be.visible')
    cy.get('input[aria-label="Space title"]:visible').first().should('be.enabled')
  })

  it('keeps the management actions for an admin, alongside join and leave', () => {
    cy.loginAs('admin')
    openCommunitiesSettings()

    cy.contains('button', 'New community').should('be.visible')
    cy.get('button[aria-label="Alpha Community Options"]:visible').should('be.visible')
    cy.get('button[aria-label="Leave Alpha"]:visible').should('be.visible')
  })
})
