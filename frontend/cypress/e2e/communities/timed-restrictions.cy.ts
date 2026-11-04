import { resetData } from '../../support/seed'

function duration(label: string) {
  cy.get('[role="dialog"]')
    .contains('button', /Until manually lifted|Keep current expiry/)
    .click()
  cy.contains('[role="option"]', new RegExp(`^${label}$`)).click()
}

function confirm(reason: string, action = 'Save restriction') {
  cy.get('[role="dialog"] textarea').type(reason)
  cy.get('[role="dialog"]').contains('button', action).click()
  cy.get('[role="dialog"]').should('not.exist')
}

describe('Timed moderation restrictions', () => {
  it('applies and lifts a timed Community ban with a reason and timezone', () => {
    resetData('space_with_discussion').then(({ community }) => {
      cy.visit(`/g/moderation?community=${community}&tab=bans`)
      cy.get('input[placeholder="Name or email"]').type('Member')
      cy.contains('[role="option"]', /^M?Member$/).click()
      cy.contains('button', 'Ban from Community').click()
      duration('1 hour')
      cy.get('[role="dialog"]').contains('Times shown in').should('be.visible')
      confirm('One hour participation restriction')
      cy.contains('One hour participation restriction').should('be.visible')
      cy.contains('button', 'Change').should('be.visible')
      cy.contains('button', 'Lift ban').click()
      cy.get('[role="dialog"]').contains('button', 'Lift restriction').should('be.disabled')
      confirm('Appeal accepted', 'Lift restriction')
      cy.contains('No active Community bans.').should('be.visible')
      cy.contains('History').click()
      cy.contains('Appeal accepted').should('be.visible')
    })
  })

  it('manages whole-site suspensions and retains history after lifting', () => {
    resetData('space_with_discussion')
    cy.visit('/g/moderation?scope=site')
    cy.contains('Applies to the entire Frappe site').should('be.visible')
    cy.get('input[placeholder="Name or email"]').type('Outsider')
    cy.contains('[role="option"]', /Outsider/).click()
    cy.contains('button', /^Suspend account$/).click()
    duration('1 day')
    confirm('Temporary account suspension')
    cy.contains('Temporary account suspension').should('be.visible')
    cy.contains('button', 'Lift suspension').click()
    confirm('Account access restored', 'Lift restriction')
    cy.contains('No active account suspensions.').should('be.visible')
    cy.get('input[placeholder="Name or email"]').type('Outsider')
    cy.contains('[role="option"]', /Outsider/).click()
    cy.contains('button', /Selected user history|View history/).click()
    cy.get('[role="dialog"]').contains('Account access restored').should('be.visible')
  })

  it('keeps account suspension controls hidden from Community staff', () => {
    resetData('space_with_discussion').then(({ community }) => {
      cy.request('POST', `/api/v2/document/GP Team/${community}/method/set_member_moderator`, {
        user: 'member2@example.com',
        is_moderator: 1,
      })
      cy.switchUser('secondMember')
      cy.visit(`/g/moderation?community=${community}&scope=site`)
      cy.contains('Community bans').should('be.visible')
      cy.contains('button', 'Account suspensions').should('not.exist')
      cy.contains('button', 'Suspend account').should('not.exist')
    })
  })
})
