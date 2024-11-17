describe('Comment', () => {
  it('comment actions', () => {
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
      .as('data')
      .then((data) => {
        let project = data[1]
        cy.request('POST', '/api/method/frappe.client.insert', {
          doc: {
            doctype: 'GP Discussion',
            project: project,
            title: 'Test discussion',
            content: 'This is a test discussion',
          },
        })
          .its('body.message')
          .then((discussion) => {
            cy.intercept('POST', '/api/method/frappe.client.get', (req) => {
              if (req.body.hasOwnProperty('doctype') && req.body.doctype === 'GP Discussion') {
                req.alias = 'getDiscussion'
              }
            })
            cy.visit(`/g/engineering/projects/${project}/discussion/${discussion.name}`)
            cy.wait('@getDiscussion')
          })
      })

    cy.intercept({
      method: 'POST',
      url: '/api/method/frappe.client.insert',
      times: 1,
    }).as('comment')
    cy.button('Add a comment').click()
    cy.focused().type('This is the first comment{enter}')
    cy.button('Submit').click()
    cy.wait('@comment')
      .its('response.body.message.content')
      .should('contain', 'This is the first comment')

    cy.get('@comment')
      .its('response.body.message')
      .then((comment) => {
        cy.intercept({
          method: 'POST',
          url: '/api/method/gameplan.extends.client.batch',
        }).as('batchRequest')
        // add a reaction
        cy.get(`div[data-id=${comment.name}] button[aria-label="Add a reaction"]`).click()
        cy.get('button:contains("👍"):visible').click()
        cy.wait('@batchRequest')
        cy.get('button:contains("👍 1")').should('exist')

        // remove a reaction
        cy.get(`div[data-id=${comment.name}] button[aria-label="Add a reaction"]`).click()
        cy.get('button:contains("💖"):visible').click()
        cy.wait('@batchRequest')
        cy.get('button:contains("💖 1")').should('exist').click()
        cy.wait('@batchRequest')
        cy.get('button:contains("💖 1")').should('not.exist')

        // edit comment
        cy.get(`div[data-id=${comment.name}] button[aria-label="Comment Options"]`).click()
        cy.button('Edit').click()
        cy.get('[contenteditable=true]')
          .clear()
          .type('This is an edited comment')
          .type('{enter}@john{enter}', { delay: 100 }) // mention user
        cy.button('Submit').click()
        cy.get(`div[data-id=${comment.name}]`).contains('This is an edited comment').should('exist')
        cy.get(`div[data-id=${comment.name}] .mention[data-id="john@example.com"]`).should('exist')

        // delete comment
        cy.intercept({
          method: 'POST',
          url: '/api/method/frappe.client.set_value',
        }).as('deleteComment')
        cy.get(`div[data-id=${comment.name}] button[aria-label="Comment Options"]`).click()
        cy.button('Delete').click()
        cy.dialog('button:contains("Delete")').click()
        cy.wait('@deleteComment')
        console.log(cy.get(`div[data-id=${comment.name}]`).contains('This message is deleted'))
        cy.get(`div[data-id=${comment.name}]`).contains('This message is deleted').should('exist')
      })
  })
})
