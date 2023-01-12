describe('Task', () => {
  it('task actions', () => {
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
        {
          doctype: 'GP Project',
          title: 'ERPNext',
          team: 'engineering',
        },
      ],
    })
      .its('body.message')
      .as('data')
      .then((data) => {
        cy.visit(`/g/engineering/projects/${data[1]}`)
        cy.get('a:contains("Tasks")').click()
        cy.url().should('include', `/g/engineering/projects/${data[1]}/tasks`)
      })
    // create task
    cy.button('New Task').click()
    cy.get('input[placeholder="Title"]').type('First Task')
    cy.get('[contenteditable=true]').type(
      'This is the description of the first task'
    )
    cy.intercept('POST', '/api/method/frappe.client.insert').as('task')
    cy.get('button').contains('Create').click()
    cy.wait('@task')
      .its('response.body.message')
      .then((task) => {
        cy.url().should(
          'include',
          `/g/engineering/projects/${task.project}/tasks/${task.name}`
        )
      })

    // edit title
    cy.iconButton('Task Options').click()
    cy.button('Edit title').click()
    cy.get('input[placeholder="Title"]').clear().type('Edited Task Title')
    cy.button('Save').click()
    cy.get('h1:contains("Edited Task Title")').should('exist')

    // assign
    cy.button('Assign a user').click()
    cy.get('li:contains("John")').click()
    cy.button('john@example.com').should('exist')

    // due date
    cy.intercept('POST', '/api/method/frappe.client.set_value').as('due_date')
    let date = new Date().toISOString().split('T')[0]
    cy.get('input[type=date]').type(date).trigger('change')
    cy.wait('@due_date')
      .its('response.body.message')
      .then((task) => {
        expect(task.due_date).to.equal(date)
        expect(task.title).to.equal('Edited Task Title')
        expect(task.assigned_to).to.equal('john@example.com')
      })

    // mark as complete
    cy.iconButton('Task Options').click()
    cy.button('Mark as complete').click()
    cy.contains('Completed').should('exist')
  })
})
