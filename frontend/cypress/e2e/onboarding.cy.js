describe('Onboarding', () => {
  it('onboarding works', () => {
    cy.login()
    cy.request({
      method: 'POST',
      url: '/api/method/gameplan.test_api.clear_data',
    })
    cy.visit('/g')

    cy.get('input[placeholder=Marketing]').type('Marketing')
    cy.get('button').contains('Next').click()
    cy.get('input[placeholder="Product Launch"]').type('Product Launch')
    cy.get('button').contains('Next').click()
    cy.get('input[placeholder="jane@example.com"]:first').type('test@example.com')
    cy.get('button').contains('Complete Setup').click()

    cy.url().should('include', '/g/marketing')

    cy.get('a:contains("Product Launch")').should('exist')
  })
})
