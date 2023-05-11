describe('Project', () => {
  it('project creation, move to team and archive', () => {
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
          doctype: 'GP Team',
          title: 'DevOps',
        },
      ],
    })
    cy.visit('/g/engineering/overview')

    cy.get('a:contains("Projects")').click()
    cy.url().should('include', '/g/engineering/projects')

    cy.intercept('POST', '/api/method/frappe.client.insert').as('project')
    cy.get('button').contains('Add Project').click()
    cy.get('label:contains("Title") input').type('Project 1')
    cy.get('button').contains('Create').click()
    cy.get('h1:contains("Project 1")').should('exist')
    cy.wait('@project')
      .its('response.body.message')
      .then((project) => {
        cy.url().should('include', `/g/engineering/projects/${project.name}`)
      })

    // move to team
    cy.get('button[aria-label="Options"]').click()
    cy.get('button:contains("Move to another team")').click()
    cy.get('button:contains("Select a team")').click()
    cy.get('li:contains("DevOps")').click()
    cy.get('button:contains("Move to DevOps")').click()
    cy.get('@project')
      .its('response.body.message')
      .then((project) => {
        cy.url().should('include', `/g/devops/projects/${project.name}`)
      })

    // archive
    cy.get('button[aria-label="Options"]').click()
    cy.get('button:contains("Archive")').click()
    cy.focused().click()
    cy.get('h1:contains("Project 1")').next().should('contain', 'Archived')
    cy.visit('/g/devops/projects')
    cy.contains('Project 1').should('not.exist')
    cy.get('button:contains("Archived")').click()
    cy.contains('Project 1').should('exist')
  })
})
