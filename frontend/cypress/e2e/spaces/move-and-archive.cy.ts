import { resetData } from '../../support/seed'

// Space management lives in the Settings dialog (Communities tab). The "Community
// actions" menu on a community's discussions page opens that dialog straight onto
// the community's spaces list, where each space exposes its "<title> Space Options"
// menu.
describe('Moving and archiving a space', () => {
  // Titles are fixed by the `two_communities` scenario; ids are not, so they come
  // from the seed.
  const betaTitle = 'Beta'
  const spaceTitle = 'Alpha Space'

  let alpha: string
  let beta: string
  let space: string

  beforeEach(() => {
    resetData('two_communities').then(({ communities = [], spaces = [] }) => {
      ;[alpha, beta] = communities
      ;[space] = spaces
    })
    cy.loginAs('admin')
  })

  function openCommunitySpaces(communityId: string) {
    cy.visit(`/g/community/${communityId}/discussions`)
    cy.iconButton('Community actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Manage spaces').first().click()
  }

  it('moves a space to another community', () => {
    cy.intercept('POST', '**/method/move_to_team').as('moveSpace')

    openCommunitySpaces(alpha)
    cy.selectDropdownOption(`${spaceTitle} Space Options`, 'Change Community')
    cy.selectCombobox('Select a community', betaTitle)
    cy.button(`Move to ${betaTitle}`).click()
    cy.wait('@moveSpace')

    // The space now resolves under the new community. If the move had not landed,
    // the router would redirect this URL back to the old community.
    cy.visit(`/g/community/${beta}/space/${space}`)
    cy.url().should('include', `/g/community/${beta}/space/${space}`)
    cy.get('header').contains(spaceTitle).should('exist')
  })

  it('archives a space and drops its pin', () => {
    cy.intercept('POST', '**/method/archive').as('archiveSpace')

    // Pinning first is the precondition for the assertion below: archiving must run
    // the backend cleanup that removes the current user's pin.
    cy.request('POST', '/api/method/frappe.client.insert', {
      doc: {
        doctype: 'GP Pinned Project',
        project: space,
      },
    })

    openCommunitySpaces(alpha)
    cy.selectDropdownOption(`${spaceTitle} Space Options`, 'Archive')
    // The archive confirmation stacks on top of the still-open Settings dialog, so
    // scope to it by title instead of asserting "no dialog".
    cy.contains('[role=dialog]', 'Archive space').as('archiveConfirm')
    cy.get('@archiveConfirm').contains('button', 'Archive').click()
    cy.wait('@archiveSpace')
    cy.contains('[role=dialog]', 'Archive space').should('not.exist')

    // Read via GET: this runs after openCommunitySpaces() has done a cy.visit,
    // so the SPA boot has installed a session CSRF token. A POST cy.request()
    // doesn't send that token and Frappe rejects it with CSRFTokenError; a GET
    // (a read) is not CSRF-checked.
    cy.request({
      method: 'GET',
      url: '/api/method/frappe.client.get_list',
      qs: {
        doctype: 'GP Pinned Project',
        filters: JSON.stringify({ project: space }),
        fields: JSON.stringify(['name']),
      },
    })
      .its('body.message')
      .should('have.length', 0)

    // Re-open the spaces list. Archived spaces are hidden until the visibility
    // filter is switched to "Archived", and render a disabled title input
    // (archived spaces are read-only).
    openCommunitySpaces(alpha)
    cy.get('input[aria-label="Space title"]:disabled').should('not.exist')
    // The visibility filter is a reka-ui Select (role=combobox); its trigger shows
    // the current value "All (N)". Switch it to "Archived" to reveal the archived
    // space.
    cy.contains('[role="combobox"]', 'All').click()
    cy.get('[role="option"]:visible').contains('Archived').click()
    cy.get('input[aria-label="Space title"]:disabled').should('have.value', spaceTitle)
  })
})
