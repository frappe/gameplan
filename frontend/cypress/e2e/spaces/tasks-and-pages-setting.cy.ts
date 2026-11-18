import { resetData } from '../../support/seed'

// The site-wide GP Settings switch that brings back the deprecated Tasks and Pages.
describe('Tasks and Pages setting', () => {
  let spaceUrl: string

  beforeEach(() => {
    resetData('space_with_discussion').then(({ community, space }) => {
      spaceUrl = `/g/community/${community}/space/${space}`
    })
    cy.loginAs('admin')
  })

  function setTasksAndPages(enabled: boolean) {
    cy.intercept('PUT', /\/api\/v2\/document\/GP(%20| )Settings\//).as('saveSettings')
    cy.visit('/g/settings/general')
    cy.scope('dialog').contains('Tasks and Pages')
    cy.scope('dialog')
      .find('[role="switch"]')
      .should('have.attr', 'aria-checked', String(!enabled))
      .click()
    cy.wait('@saveSettings').its('response.statusCode').should('eq', 200)
    cy.scope('dialog')
      .find('[role="switch"]')
      .should('have.attr', 'aria-checked', String(enabled))
  }

  it('is off by default, so a space has no Tasks or Pages', () => {
    cy.visit(spaceUrl)
    cy.contains('button', 'All discussions').should('be.visible')
    cy.contains('[role="radio"]', 'Tasks').should('not.exist')

    cy.visit(`${spaceUrl}/tasks`)
    cy.url().should('include', '/discussions')
    cy.visit(`${spaceUrl}/pages`)
    cy.url().should('include', '/discussions')
  })

  it('brings the space tabs back when an admin turns it on, and hides them again', () => {
    setTasksAndPages(true)

    cy.visit(spaceUrl)
    cy.contains('[role="radio"]', 'Tasks').click()
    cy.url().should('include', '/tasks')
    cy.button('New task').should('be.visible')

    cy.contains('[role="radio"]', 'Pages').click()
    cy.url().should('include', '/pages')
    cy.button('New page').should('be.visible')

    setTasksAndPages(false)

    cy.visit(`${spaceUrl}/tasks`)
    cy.url().should('include', '/discussions')
    cy.contains('[role="radio"]', 'Tasks').should('not.exist')
  })

  it('is not offered to members', () => {
    cy.loginAs('member')
    cy.visit('/g/settings/preferences')
    cy.scope('dialog').contains('Preferences')
    cy.scope('dialog').contains('General').should('not.exist')
  })
})
