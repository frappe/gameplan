import { resetData } from '../../support/seed'

it('focuses a linked public reply when its page is loaded later', () => {
  resetData('public_space').then((ids) => {
    cy.clearCookies()
    cy.request({
      url: '/api/v2/method/gameplan.public_lists.comments',
      qs: {
        fields: JSON.stringify([
          'name',
          'content',
          'owner',
          'creation',
          'reference_doctype',
          'reference_name',
        ]),
        filters: JSON.stringify({
          reference_doctype: 'GP Discussion',
          reference_name: ids.discussion,
        }),
      },
    }).then(({ body }) => {
      const reply = body.data[0]
      // Exercise the 1,000-row page boundary without creating 1,000 unrelated replies.
      cy.intercept('GET', '**/gameplan.public_lists.comments*', (req) => {
        req.reply({
          body:
            Number(req.query.start) === 0
              ? { data: [], has_next_page: true }
              : { data: [reply], has_next_page: false },
        })
      }).as('comments')
      cy.visit(
        `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}?comment=${reply.name}`,
      )
      cy.wait('@comments')
      cy.get(`div[data-id="${reply.name}"]`).should('not.exist')
      cy.contains('button', 'Load more comments').click()
      cy.wait('@comments').its('request.query.start').should('eq', '1000')
      cy.get(`div[data-id="${reply.name}"] > .border-2`).should('exist')
      cy.contains('Glad to be here.').should('be.visible')
    })
  })
})
