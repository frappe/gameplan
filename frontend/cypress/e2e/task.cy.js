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
        cy.contains('h2', 'Tasks').parent('div').contains('button', 'View all').click()
        cy.url().should('include', `/g/engineering/projects/${data[1]}/tasks`)
      })

    // create task
    cy.button('Add new').click()
    cy.contains('label', 'Title').parent().find('input').type('First Task')
    cy.get('textarea').type('This is the description of the first task')
    cy.intercept('POST', '/api/method/frappe.client.insert').as('task')
    cy.get('button').contains('Create').click()
    cy.wait('@task')
      .its('response.body.message')
      .then((task) => {
        cy.get(`a:contains(${task.name})`).should('exist').click()
      })

    cy.get('input[placeholder="Title"]').click().clear({ force: true }).type('Edited Task Title')
    cy.get('body').click()

    cy.intercept('POST', '/api/method/frappe.client.set_value').as('title')
    cy.wait('@title')
      .its('response.body.message')
      .then((task) => {
        cy.get('input[placeholder="Title"]').should('have.value', task.title).and('exist')
      })

    // assign
    cy.intercept('POST', '/api/method/frappe.client.set_value').as('assign_user')
    cy.button('Assign a user').click()
    cy.get('li[id^="headlessui-combobox-option-"]:visible').contains('John Doe').click()

    cy.wait('@assign_user')
      .its('response.body.message')
      .then((task) => {
        task.assigned_to = 'john@example.com'
      })

    // set due date
    let date = new Date()
    cy.intercept('POST', '/api/method/frappe.client.set_value').as('due_date')
    cy.get("input[placeholder='Due date']").last().click()
    cy.get('div')
      .contains(new RegExp(`^${String(date.getDate())}$`))
      .click({ force: true })
    cy.wait('@due_date')
      .its('response.body.message')
      .then((task) => {
        task.due_date = date.toISOString().split('T')[0]
      })

    cy.reload()

    cy.contains('div', 'Status').next('div').find('button').click()
    cy.contains('button', 'Done').should('be.visible').click()
  })
})
