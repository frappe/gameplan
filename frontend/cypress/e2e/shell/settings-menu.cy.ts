// Settings must be reachable from the account (avatar) menu, not only from the
// app logo menu — the avatar is where people look for it first.
import { resetData } from '../../support/seed'

describe('Settings entry points', () => {
  beforeEach(() => {
    resetData('onboarded')
    cy.loginAs('member')
    cy.visit('/g')
    cy.url().should('include', '/discussions')
  })

  it('opens the settings dialog from the account menu', () => {
    cy.selectDropdownOption('Account menu', 'Settings')

    cy.location('pathname').should('equal', '/g/settings/profile')
    cy.contains('[role="dialog"]', 'User settings').should('be.visible')
  })

  it('opens the settings dialog from the app menu', () => {
    cy.selectDropdownOption('Gameplan menu', 'Settings')

    cy.location('pathname').should('equal', '/g/settings/profile')
    cy.contains('[role="dialog"]', 'User settings').should('be.visible')
  })
})
