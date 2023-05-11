describe('Team', () => {
  it('team creation, readme edit and archive', () => {
    cy.login()
    cy.request({
        method: 'POST',
        url: '/api/method/gameplan.test_api.clear_data?onboard=1',
    })
    cy.visit('/g')
    cy.get('button[aria-label="Create Team"]').click()
    cy.get('input[placeholder="Team Name"]').type('Engineering')
    cy.get('button').contains('Create Team').click()
    cy.url().should('include', '/g/engineering/overview')

    cy.intercept('POST', '/api/method/frappe.client.set_value').as('set_value')
    cy.get('button[aria-label="Edit"]').click()
    cy.focused().type(
      '{selectAll}{backspace}## Engineering 2{enter}some description'
    )
    cy.get('button').contains('Save').click()
    cy.get('button').contains('Save').should('not.exist')
    cy.get('h2').contains('Engineering 2').should('exist')
    cy.get('@set_value').its('response.statusCode').should('eq', 200)

    cy.get('button[aria-label="Options"]').click()
    cy.get('button').contains('Archive').click()
    cy.dialog('button').contains('Archive').click()
    cy.contains('Engineering').should('not.exist')

    cy.get('button').contains('Administrator').click()
    cy.get('button').contains('Settings').click()
    cy.dialog('button').contains('Archived Teams').click()

    cy.contains('Engineering').should('exist')
  })
})
