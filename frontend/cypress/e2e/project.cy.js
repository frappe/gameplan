describe('Project', () => {
  it('project creation, discussion and task creation', () => {
    cy.login()
    cy.request('/api/method/gameplan.test_api.clear_data?onboard=1')
    cy.request('POST', '/api/method/frappe.client.insert', {
      doc: {
        doctype: 'Team',
        title: 'Engineering',
      },
    })
    cy.visit('/g/engineering/overview')

    cy.get('a:contains("Projects")').click()
    cy.url().should('include', '/g/engineering/projects')

    cy.intercept('POST', '/api/method/frappe.client.insert').as('project')
    cy.get('button').contains('New Project').click()
    cy.get('label:contains("Title") input').type('Project 1')
    cy.get('button').contains('Create').click()
    cy.get('h1:contains("Project 1")').should('exist')
    cy.get('@project')
      .its('response.body.message')
      .then((project) => {
        cy.url().should('include', `/g/engineering/projects/${project.name}`)
      })

    // create discussion
    cy.get('a:contains("Discussions")').click()
    cy.get('button:contains("New Discussion")').click()

    cy.focused().type('Starting a new discussion')
    cy.get('div[contenteditable=true]')
      .click()
      .type('This is content for new discussion{enter}')

    cy.intercept('POST', '/api/method/frappe.client.insert').as('discussion')
    cy.get('button').contains('Publish').click()

    cy.get('@discussion')
      .its('response.body.message')
      .then((discussion) => {
        cy.url().should(
          'include',
          `/g/engineering/projects/${discussion.project}/discussion/${discussion.name}/starting-a-new-discussion`
        )
      })

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
