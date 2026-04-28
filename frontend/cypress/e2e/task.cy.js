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
          doctype: 'GP Project',
          title: 'Gameplan',
        },
        {
          doctype: 'GP Project',
          title: 'ERPNext',
        },
      ],
    })
      .its('body.message')
      .as('data')
      .then((data) => {
        cy.visit(`/g/space/${data[1]}/tasks`)
        cy.get('[role=radio][aria-checked="true"]').contains('Tasks').should('exist')
      })

    // create task
    cy.button('Add new').click()
    cy.contains('label', 'Title').parent().find('input').type('First Task')
    cy.get('textarea').type('This is the description of the first task')
    cy.intercept('POST', '/api/v2/document/GP%20Task').as('task')
    cy.get('button').contains('Create').click()
    cy.wait('@task')
      .its('response.body.data')
      .then((task) => {
        cy.get(`a:contains(${task.name})`).should('exist').click()
      })

    cy.intercept('PUT', '/api/v2/document/GP%20Task/*').as('title')
    cy.get('input[placeholder="Title"]').click().clear({ force: true }).type('Edited Task Title')
    cy.get('body').click()

    cy.wait('@title')
      .its('response.body.data')
      .then((task) => {
        cy.get('input[placeholder="Title"]').should('have.value', task.title).and('exist')
      })

    // assign
    cy.intercept('PUT', '/api/v2/document/GP%20Task/*').as('assign_user')
    // cy.button('Assign a user').click()
    cy.selectCombobox('Assign a user', 'John Doe')
    // cy.get('li[id^="headlessui-combobox-option-"]:visible').contains('John Doe').click()

    cy.wait('@assign_user')
      .its('response.body.data')
      .then((task) => {
        task.assigned_to = 'john@example.com'
      })

    // set due date
    let date = new Date()
    cy.intercept('PUT', '/api/v2/document/GP%20Task/*').as('due_date')
    cy.get("input[placeholder='Due date']:visible")
      .clear()
      .type(date.toISOString().split('T')[0], { force: true })
      .blur()
    cy.wait('@due_date')
      .its('response.body.data')
      .then((task) => {
        task.due_date = date.toISOString().split('T')[0]
      })

    cy.contains('div', 'Status').next('div').find('button').click()
    cy.get('[role="menuitem"]:contains("Done"):visible').click()
  })
})
