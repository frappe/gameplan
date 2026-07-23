import { resetData } from '../../support/seed'

// Every step here acts on the one comment the user just posted, so this stays a
// single flow: there is no seeded comment to react to, edit, or delete.
describe('Comment actions', () => {
  let community: string
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
    })
    cy.loginAs('member')
  })

  it('posts a comment, reacts to it, edits it with a mention, and deletes it', () => {
    cy.intercept('GET', `/api/v2/document/GP%20Discussion/${discussion}`).as('getDiscussion')
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)
    cy.wait('@getDiscussion')

    cy.intercept({
      method: 'POST',
      url: '/api/v2/document/GP%20Comment',
      times: 1,
    }).as('comment')
    cy.button('Add a comment').click()
    // Click the editor to settle focus before typing — relying on the auto-focus
    // via cy.focused() races the just-mounted ProseMirror view and drops the
    // first keystroke. Submit via the button (not {enter}) to avoid a premature
    // submit of partial text.
    cy.get('[contenteditable=true]').should('be.visible').click().type('This is the first comment')
    cy.button('Submit').click()
    cy.wait('@comment')
      .its('response.body.data.content')
      .should('contain', 'This is the first comment')

    cy.get('@comment')
      .its('response.body.data')
      .then((comment: { name: string }) => {
        const commentSelector = `div[data-id="${comment.name}"]`

        cy.intercept({
          method: 'POST',
          url: `/api/v2/document/GP%20Comment/${comment.name}/method/react`,
        }).as('reactRequest')

        // add a reaction
        cy.get(`${commentSelector} button[aria-label="Add a reaction"]`).click()
        cy.get('button:contains("👍"):visible').click()
        cy.wait('@reactRequest')
        // The reaction pill separates emoji and count with a non-breaking space,
        // so match with a regex (\s covers U+00A0) instead of a literal space.
        cy.contains('button', /👍\s*1/).should('exist')
        cy.get(commentSelector).contains('Edited').should('not.exist')

        // remove a reaction
        cy.get(`${commentSelector} button[aria-label="Add a reaction"]`).click()
        cy.get('button:contains("💖"):visible').click()
        cy.wait('@reactRequest')
        cy.contains('button', /💖\s*1/)
          .should('exist')
          .click()
        cy.wait('@reactRequest')
        cy.contains('button', /💖\s*1/).should('not.exist')

        // edit the comment, mentioning the community's other member
        cy.selectDropdownOption('Comment Options', 'Edit')
        cy.get('[contenteditable=true]')
          .clear()
          .type('This is an edited comment')
          .type('{enter}@Second{enter}', { delay: 100 }) // mention Second Member
        cy.button('Submit').click()
        cy.get(commentSelector).contains('This is an edited comment').should('exist')
        cy.get(commentSelector).contains('Edited').should('exist')
        cy.get(`${commentSelector} [data-type="mention"][data-id="member2@example.com"]`).should(
          'exist',
        )

        // delete the comment
        cy.intercept({
          method: 'DELETE',
          url: `/api/v2/document/GP%20Comment/${comment.name}`,
        }).as('deleteComment')
        cy.selectDropdownOption('Comment Options', 'Delete')
        cy.dialog('button:contains("Delete")').click()
        cy.wait('@deleteComment')
        cy.get(commentSelector).should('not.exist')
      })
  })
})
