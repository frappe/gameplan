import { resetData } from '../../support/seed'

describe('Community moderator assignments', () => {
  beforeEach(() => {
    resetData('two_communities')
    cy.loginAs('admin')
    cy.visit('/g/settings/communities/alpha/members')
  })

  const memberRow = () => cy.contains('[data-slot="list-row"]', 'Second Member')

  it('appoints and removes a moderator without changing their membership', () => {
    cy.selectDropdownOption('Second Member Member Options', 'Make community moderator')
    cy.contains('button', 'Make Moderator').click()
    memberRow().should('contain.text', 'Moderator')

    cy.reload()
    memberRow().should('contain.text', 'Moderator')

    cy.selectDropdownOption('Second Member Member Options', 'Remove community moderator')
    cy.contains('button', 'Remove Moderator').click()
    memberRow().should('not.contain.text', 'Moderator').and('contain.text', 'Member')

    cy.reload()
    memberRow().should('not.contain.text', 'Moderator').and('contain.text', 'Second Member')
  })
})
