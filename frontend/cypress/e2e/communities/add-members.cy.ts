// Adding members is the community manager's bulk action: search the people who
// are not in the community yet, tick as many as you want, add them in one call.
import { resetData } from '../../support/seed'

describe('Adding members to a community', () => {
  beforeEach(() => {
    resetData('two_communities')
    // Administrator manages every community, so the Add members trigger is there.
    cy.loginAs('admin')
    cy.visit('/g/settings/communities/alpha/members')
    cy.contains('button:visible', 'Add members').should('be.visible')
  })

  // The settings screen is itself a dialog, so scope by something only the
  // picker has.
  const picker = () => cy.get('[role="dialog"]').filter(':has(input[aria-label="Search people"])')
  const pickerRows = () => cy.get('[aria-label="People you can add"] [data-slot="list-row"]')
  const selectAll = () => picker().contains('label', /^Select /)

  const openPicker = () => {
    cy.contains('button:visible', 'Add members').click()
    cy.get('input[aria-label="Search people"]').should('be.visible')
  }

  it('lists only the people who are not members yet', () => {
    openPicker()

    pickerRows().should('have.length.at.least', 1)
    pickerRows().contains('Outsider').should('be.visible')
    // Alpha's seeded members are already in, so they are not offered again.
    pickerRows().contains('Second Member').should('not.exist')

    picker().contains('0 selected').should('be.visible')
    picker().contains('button', 'Add members').should('be.disabled')
  })

  it('filters the list as you search', () => {
    openPicker()

    cy.get('input[aria-label="Search people"]').type('outsider')
    pickerRows().should('have.length', 1)
    pickerRows().contains('Outsider').should('be.visible')
    selectAll().should('contain.text', 'Select 1 matching')

    cy.get('input[aria-label="Search people"]').clear().type('nobodyhasthisname')
    cy.contains('No people match your search.').should('be.visible')
  })

  it('selects every addable person at once and counts them on the button', () => {
    openPicker()

    pickerRows().then(($rows) => {
      const count = $rows.length
      selectAll().click()

      picker().contains(`${count} selected`).should('be.visible')
      const label = count === 1 ? 'Add 1 member' : `Add ${count} members`
      picker().contains('button', label).should('be.enabled')
    })
  })

  it('adds everyone selected in one submit', () => {
    openPicker()

    pickerRows().then(($rows) => {
      const count = $rows.length
      selectAll().click()
      const label = count === 1 ? 'Add 1 member' : `Add ${count} members`
      picker().contains('button', label).click()
    })

    // The picker closes and the members list behind it picks up the new rows.
    cy.get('input[aria-label="Search people"]').should('not.exist')
    cy.contains(/added to Alpha/).should('be.visible')
    cy.contains('[data-slot="list-row"]', 'Outsider').should('be.visible')

    // Reopening offers nobody: everyone belongs to the community now.
    cy.contains('button:visible', 'Add members').click()
    cy.contains('Everyone already belongs to this community.').should('be.visible')
  })
})
