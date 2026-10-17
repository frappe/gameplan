import { resetData } from '../../support/seed'

describe('Reply moderation', () => {
  it('hides, privately previews, and restores a reply as a community moderator', () => {
    let path: string
    let comment: string
    const reply = () => cy.get(`div[data-id="${comment}"]`)

    resetData('space_with_discussion').then((ids) => {
      path = `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`
      cy.request({
        method: 'POST',
        url: `/api/v2/document/GP%20Team/${ids.community}/method/set_member_moderator`,
        body: { user: 'member2@example.com', is_moderator: 1 },
      })
      cy.loginAs('member')
      cy.request({
        method: 'POST',
        url: '/api/v2/document/GP%20Comment',
        body: {
          reference_doctype: 'GP Discussion',
          reference_name: ids.discussion,
          content: '<p>Reply moderation browser sentinel</p>',
        },
      }).then(({ body }) => {
        comment = String(body.data.name)
      })
      cy.loginAs('secondMember')
      cy.visit(path)
    })

    cy.then(() => {
      reply().should('contain.text', 'Reply moderation browser sentinel')
      reply().find('button[aria-label="Comment Options"]').click()
      cy.contains('[role="menuitem"]', 'Hide reply').click()
      cy.get('[role="menu"]').should('not.exist')
      cy.get('[role="dialog"] textarea').type('Spam')
      cy.get('[role="dialog"]').contains('button', 'Hide reply').click()
      reply().should('contain.text', 'This reply was hidden by a moderator.')
      reply().should('not.contain.text', 'Reply moderation browser sentinel')
      reply().contains('button', 'View hidden reply').click()
      reply().should('contain.text', 'Reply moderation browser sentinel')

      cy.switchUser('member')
      cy.then(() => cy.visit(path))
      reply().should('contain.text', 'This reply was hidden by a moderator.')
      reply().should('not.contain.text', 'Reply moderation browser sentinel')
      reply().contains('button', 'View hidden reply').should('not.exist')

      cy.switchUser('secondMember')
      cy.then(() => cy.visit(path))
      reply().find('button[aria-label="Comment Options"]').click()
      cy.contains('[role="menuitem"]', 'Restore reply').click()
      cy.get('[role="menu"]').should('not.exist')
      cy.get('[role="dialog"]').contains('button', 'Restore reply').click()
      reply().should('contain.text', 'Reply moderation browser sentinel')
      cy.reload()
      reply().should('contain.text', 'Reply moderation browser sentinel')
      reply().should('not.contain.text', 'This reply was hidden by a moderator.')
    })
  })
})
