describe('Discussion', () => {
  it('all discussion actions', () => {
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
        // cy.get('a:contains("Discussions")').click()
      })

    // create discussion
    cy.intercept({
      method: 'POST',
      url: '/api/method/frappe.client.insert',
      times: 1,
    }).as('discussion')
    // edit following cypress test to select the div with h2 tag containing Discussions and then click the button that ocntains View all thats within the same div
    cy.contains('h2', 'Discussions').parents('div').contains('button', 'View all').click()

    // cy.button('View all').click()
    cy.button('Add new').click()
    cy.get('textarea').type('Starting a new discussion')
    cy.get('div[contenteditable=true]').click().type('This is content for new discussion{enter}')
    cy.get('button').contains('Publish').click()
    cy.wait('@discussion')
      .its('response.body.message')
      .then((discussion) => {
        cy.url().should(
          'include',
          `/g/engineering/projects/${discussion.project}/discussion/${discussion.name}/starting-a-new-discussion`,
        )
      })

    // cy.get('button').contains(' Add new ').click()

    // add comment
    cy.intercept('POST', '/api/method/frappe.client.insert').as('comment')
    cy.button('Add a comment').click()
    cy.focused().type('This is the first comment{enter}')
    cy.button('Submit').click()
    cy.wait('@comment')
      .its('response.body.message')
      .then((comment) => {
        cy.get(`div[data-id="${comment.name}"]`).should('exist')
      })

    // edit title
    cy.iconButton('Discussion Options').click()
    cy.button('Edit').click()
    cy.get('input[placeholder="Title"]')
      .type(' {selectall}', { delay: 200 })
      .type('Edited Discussion Title')
    cy.button('Submit').click()
    cy.get('h1:contains("Edited Discussion Title")').should('exist')
    cy.contains(
      'changed the title from "Starting a new discussion" to "Edited Discussion Title"',
    ).should('exist')

    // edit content
    cy.iconButton('Discussion Options').click()
    cy.button('Edit').click()
    cy.get('[contenteditable=true]')
      .type('{enter}{enter}', { delay: 200 })
      .type('adding more content')
    cy.button('Submit').click()
    cy.get('p:contains("adding more content")').should('exist')

    // move to another project
    cy.iconButton('Discussion Options').click()
    cy.button('Move to...').click()
    cy.button('Select a project').click()
    cy.get('li:contains("ERPNext")').click()
    cy.button('Move to ERPNext').click()

    cy.get('@data').then((data) => {
      let erpnextProject = data[2]
      cy.get('@discussion')
        .its('response.body.message')
        .then((discussion) => {
          cy.url().should(
            'include',
            `/g/engineering/projects/${erpnextProject}/discussion/${discussion.name}`,
          )
        })
    })

    // close discussion
    cy.iconButton('Discussion Options').click()
    cy.button('Close discussion').click()
    cy.dialog('button').contains('Close').click()
    cy.contains('closed this discussion').should('exist')
    cy.button('Add a comment').should('not.exist')
  })
})
