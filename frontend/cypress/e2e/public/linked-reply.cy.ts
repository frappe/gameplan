import { resetData } from '../../support/seed'

it('opens and highlights a linked public reply on its current page', () => {
  resetData('public_space').then((ids) => {
    cy.request('POST', '/api/method/frappe.client.insert_many', {
      docs: Array.from({ length: 50 }, (_, i) => ({
        doctype: 'GP Comment',
        reference_doctype: 'GP Discussion',
        reference_name: ids.discussion,
        content: `<p>Linked reply ${i + 1}</p>`,
      })),
    }).then(({ body }) => {
      const reply = String(body.message[49])
      cy.clearCookies()
      cy.intercept('GET', '**/gameplan.public_lists.comments*').as('comments')
      cy.visit(
        `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}?comment=${reply}`,
      )
      cy.wait('@comments').its('request.query.start').should('eq', '50')
      cy.location('search').should('include', 'page=2').and('include', `comment=${reply}`)
      cy.get(`div[data-id="${reply}"] > .border-2`).should('exist')
      cy.contains('Linked reply 50').should('be.visible')
    })
  })
})
