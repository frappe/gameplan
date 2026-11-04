// The settings dialog keeps its URLs, but it is a layer over a page, not a page of its
// own: browser history moves between pages and passes over it. Phones are the exception,
// because settings is an ordinary page there.
import { resetData } from '../../support/seed'

describe('Settings dialog and browser history', () => {
  const dialog = () => cy.get('[role="dialog"]:visible')
  const dialogClosed = () => cy.get('[role="dialog"]:visible').should('not.exist')
  const pathIs = (path: string) => cy.location('pathname').should('equal', path)
  const openFromAccountMenu = () => {
    cy.selectDropdownOption('Account menu', 'Settings')
    pathIs('/g/settings/profile')
    dialog().should('be.visible')
  }
  const selectTab = (label: string) => dialog().contains('[role="tab"]', label).click()
  const visitTwoPages = () => {
    cy.visit('/g/notifications')
    pathIs('/g/notifications')
    cy.visit('/g/people')
    pathIs('/g/people')
  }

  // Every row's Spaces button reads like "2 spaces", so scope it to Alpha's row.
  const openAlphaSpaces = () =>
    dialog()
      .contains('div', /^Alpha$/)
      .parents()
      .filter(':has(button:visible)')
      .first()
      .contains('button:visible', /space/i)
      .click()

  describe('on desktop', () => {
    beforeEach(() => {
      resetData('two_communities')
      cy.loginAs('outsider')
    })

    it('leaves the dialog in one Back, however many tabs were visited', () => {
      visitTwoPages()
      openFromAccountMenu()
      selectTab('Preferences')
      pathIs('/g/settings/preferences')
      selectTab('Notifications')
      pathIs('/g/settings/notifications')

      cy.go('back')
      pathIs('/g/people')
      dialogClosed()

      cy.go('forward')
      pathIs('/g/settings/notifications')
      dialog().should('be.visible')
    })

    it('does not reopen after closing', () => {
      visitTwoPages()
      openFromAccountMenu()
      selectTab('Preferences')
      cy.get('body').type('{esc}')
      pathIs('/g/people')
      dialogClosed()

      cy.go('back')
      pathIs('/g/notifications')
      dialogClosed()
    })

    describe('on a cold load', () => {
      beforeEach(() => {
        cy.visit('/g/settings/preferences')
        dialog().should('be.visible')
      })

      it('closes to Home', () => {
        cy.get('body').type('{esc}')
        dialogClosed()
        cy.location('pathname').should('not.include', '/settings')
      })

      it('goes Back to Home', () => {
        cy.go('back')
        dialogClosed()
        cy.location('pathname').should('not.include', '/settings')
      })
    })

    it('closes to the original page after a reload', () => {
      visitTwoPages()
      openFromAccountMenu()
      cy.reload()
      dialog().should('be.visible')
      cy.get('body').type('{esc}')
      pathIs('/g/people')
      dialogClosed()
    })

    it('walks community detail back to the list, and closes past both', () => {
      visitTwoPages()
      openFromAccountMenu()
      selectTab('Communities')
      openAlphaSpaces()
      pathIs('/g/settings/communities/alpha/spaces')

      cy.go('back')
      pathIs('/g/settings/communities')
      dialog().should('be.visible')

      openAlphaSpaces()
      pathIs('/g/settings/communities/alpha/spaces')
      cy.get('body').type('{esc}')
      pathIs('/g/people')
      dialogClosed()
    })

    it('does not stack entries through the Back to communities button', () => {
      visitTwoPages()
      openFromAccountMenu()
      selectTab('Communities')
      openAlphaSpaces()
      pathIs('/g/settings/communities/alpha/spaces')
      cy.get('button[aria-label="Back to communities"]:visible').click()
      pathIs('/g/settings/communities')

      cy.go('back')
      pathIs('/g/people')
      dialogClosed()
    })

    it('drops the dialog from history when a link leaves it for a page', () => {
      visitTwoPages()
      openFromAccountMenu()
      cy.contains('[role="dialog"] button:visible', 'View').click()
      cy.location('pathname').should('match', /^\/g\/people\/.+/)
      dialogClosed()

      cy.go('back')
      pathIs('/g/people')
      dialogClosed()
    })
  })

  it('keeps ordinary page history on a phone', () => {
    cy.viewport('iphone-6')
    resetData('onboarded')
    cy.loginAs('member')
    cy.visit('/g/more')
    cy.contains('Preferences').scrollIntoView().click()
    pathIs('/g/settings/preferences')

    cy.go('back')
    pathIs('/g/more')
  })
})
