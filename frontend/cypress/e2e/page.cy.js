describe('Page', () => {
  it('creates a page from a space and returns to the pages tab', () => {
    cy.login()
    cy.request({
      method: 'POST',
      url: '/api/method/gameplan.test_api.clear_data?onboard=1',
    })
    cy.request('POST', '/api/method/frappe.client.insert_many', {
      docs: [
        {
          doctype: 'GP Team',
          title: 'Engineering',
        },
        {
          doctype: 'GP Project',
          title: 'Gameplan',
          team: 'engineering',
        },
      ],
    })
      .its('body.message')
      .then((data) => {
        let space = data[1]
        cy.visit(`/g/space/${space}/pages`)
        cy.button('Add new').click()
        cy.url().should('include', `/g/space/${space}/pages/`)
        cy.get('input[placeholder="Title"]').should('have.value', 'Untitled')
        cy.get('header').contains('a', 'Pages').click()
        cy.url().should('eq', `${Cypress.config().baseUrl}/g/space/${space}/pages`)
        cy.contains('a', 'Untitled').should('exist')
      })
  })
})
