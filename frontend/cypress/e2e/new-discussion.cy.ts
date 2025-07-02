describe('New Discussion - Draft Functionality', () => {
  let testData: any

  beforeEach(() => {
    cy.login()
    // Clear data and set up test environment
    cy.request({
      method: 'POST',
      url: '/api/method/gameplan.test_api.clear_data?onboard=1',
    })

    // Create test teams and projects
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
        testData = data
      })
  })

  it('should create, save, and verify a draft', () => {
    // Navigate to new discussion page via proper flow
    cy.visit('/g/discussions')
    cy.button('Drafts').click()
    cy.button('Add new').click()

    // Verify page loads correctly
    cy.contains('New Discussion').should('exist')
    cy.get('textarea[placeholder="Title"]').should('exist')
    cy.get('[contenteditable=true]').should('exist')

    // create the draft
    cy.get('textarea[placeholder="Title"]').type('My Draft Discussion')
    cy.get('[contenteditable=true]').click().type('This is my draft content that should be saved.')
    cy.combobox('Select Space').click().type('Gameplan').type('{enter}')
    cy.button('Save Draft').click()

    // Go back to drafts
    cy.visit('/g/discussions/drafts')

    // Verify if the draft was created
    cy.contains('My Draft Discussion').should('exist')
    cy.contains('Gameplan: This is my draft content that should be saved.').should('exist')

    // Click on the draft to edit it
    cy.contains('My Draft Discussion').click()

    // Make some changes to the content
    cy.get('textarea[placeholder="Title"]').should('have.value', 'My Draft Discussion')
    cy.get('[contenteditable=true]')
      .click()
      .clear()
      .type('This is my updated draft content. Ready to publish!')

    // Publish the discussion
    cy.button('Publish').click()

    // Verify the discussion was published successfully
    cy.url().should('not.include', '/drafts')
    cy.contains('My Draft Discussion').should('exist')
    cy.contains('This is my updated draft content. Ready to publish!').should('exist')

    // Go back to drafts and verify the draft no longer exists
    cy.visit('/g/discussions/drafts')
    cy.contains('My Draft Discussion').should('not.exist')
  })
})
