import { resetData } from '../../support/seed'

describe('Reply moderation', () => {
  it('refreshes an open reader thread when another session hides or restores a reply', () => {
    resetData('space_with_discussion').then((ids) => {
      cy.loginAs('member')
      cy.request({
        method: 'PUT',
        url: `/api/v2/document/GP%20Discussion/${ids.discussion}`,
        body: {
          content: '<p>A long discussion keeps the reader above the moderated reply.</p>'.repeat(
            70,
          ),
        },
      })
      cy.request({
        method: 'POST',
        url: '/api/v2/document/GP%20Comment',
        body: {
          reference_doctype: 'GP Discussion',
          reference_name: ids.discussion,
          content: '<p>Live moderation sentinel</p>',
        },
      }).then(({ body }) => {
        const reply = () => cy.get(`div[data-id="${body.data.name}"]`)
        const scrollContainer =
          '[data-slot="desktop-shell-content"] > * > [data-reka-scroll-area-viewport]'
        const assertReadingPosition = () => {
          // Automatic scrolling used to run 50–150 ms after the list refreshed.
          cy.wait(200)
          cy.get(scrollContainer).should(($el) => expect($el[0].scrollTop).to.be.closeTo(200, 2))
        }
        const moderate = (method: 'hide' | 'restore') => {
          cy.task('requestAsUser', {
            user: 'Administrator',
            path: `/api/v2/document/GP Comment/${body.data.name}/method/${method}`,
            body: method === 'hide' ? { reason: 'Spam' } : {},
          })
          // Dispatch to mounted listeners; this regression does not need a Socket.IO server.
          cy.window().then((win) => {
            const app = (win.document.querySelector('#app') as any).__vue_app__
            const socket = app.config.globalProperties.$socket
            const listeners = socket.listeners('new_activity')
            expect(listeners, 'mounted activity listeners').not.to.be.empty
            listeners.forEach((listener: (data: unknown) => void) =>
              listener({
                reference_doctype: 'GP Discussion',
                reference_name: String(ids.discussion),
              }),
            )
          })
        }
        cy.visit(
          `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`,
        )
        reply().should('contain.text', 'Live moderation sentinel')
        cy.get(scrollContainer).should(($el) => {
          expect($el[0].scrollTop).to.be.closeTo($el[0].scrollHeight - $el[0].clientHeight, 2)
        })
        cy.get(scrollContainer).scrollTo(0, 200)
        moderate('hide')
        reply().should('contain.text', 'This reply was hidden by a moderator.')
        reply().should('not.contain.text', 'Live moderation sentinel')
        reply().contains('button', 'View hidden reply').should('not.exist')
        assertReadingPosition()
        moderate('restore')
        reply().should('contain.text', 'Live moderation sentinel')
        reply().should('not.contain.text', 'This reply was hidden by a moderator.')
        assertReadingPosition()
        cy.contains('button', 'Add a comment').click()
        cy.get('[contenteditable=true]').click().type('A newly submitted reply')
        cy.contains('button', 'Submit').click()
        cy.contains('A newly submitted reply').should('exist')
        cy.get(scrollContainer).should(($el) => {
          expect($el[0].scrollTop).to.be.closeTo($el[0].scrollHeight - $el[0].clientHeight, 2)
        })
      })
    })
  })

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
