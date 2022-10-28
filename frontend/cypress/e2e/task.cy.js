describe('Discussion', () => {
  it('creating a discussion', () => {
    // create task
    cy.get('a:contains("Tasks")').click()
    cy.get('button:contains("New Task")').click()
    cy.get('input[placeholder="Title"]').type('First Task')
    cy.get('[contenteditable=true]').type(
      'This is the description of the first task'
    )
    cy.intercept('POST', '/api/method/frappe.client.insert').as('task')
    cy.get('button').contains('Create').click()
    cy.get('@task')
      .its('response.body.message')
      .then((task) => {
        cy.url().should(
          'include',
          `/g/engineering/projects/${task.project}/tasks/${task.name}`
        )
      })
  })
})
