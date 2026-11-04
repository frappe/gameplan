import { resetData } from '../../support/seed'

// One happy path: member2 mentions member in a reply, member's bell badge picks it up,
// and "Mark all as read" clears both the list and the badge. Who gets notified (and
// who must not) is the backend suite's job — gameplan/tests/features/test_notifications.py.
describe('Notifications', () => {
  let community: string
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
    })
  })

  it('badges a mention, lists it, and clears it with mark all as read', () => {
    // member2 replies to member's discussion, mentioning member
    cy.loginAs('secondMember')
    cy.intercept('GET', `/api/v2/document/GP%20Discussion/${discussion}`).as('getDiscussion')
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)
    cy.wait('@getDiscussion')

    cy.intercept({ method: 'POST', url: '/api/v2/document/GP%20Comment', times: 1 }).as('comment')
    cy.button('Add a comment').click()
    // Click the editor to settle focus before typing — the auto-focus races the
    // just-mounted ProseMirror view and drops the first keystroke. The mention
    // suggestion list filters on label prefix, so "@Member" offers only Member
    // (not "Second Member"), and {enter} accepts the highlighted entry.
    cy.get('[contenteditable=true]').should('be.visible').click().type('Please take a look ')
    cy.get('[contenteditable=true]').type('@Member{enter}', { delay: 100 })
    cy.get('[contenteditable=true] [data-type="mention"][data-id="member@example.com"]').should(
      'exist',
    )
    cy.button('Submit').click()
    cy.wait('@comment').its('response.body.data.content').should('contain', 'member@example.com')

    // member lands on an unread badge in the rail. `switchUser` (not `loginAs`) because
    // member2's page is still loaded: its in-flight requests would otherwise re-set the
    // `sid` cookie back to member2 and boot the next visit as the wrong user.
    cy.switchUser('member')
    // The count is a `useCall` GET, so its URL carries a (here empty) query string —
    // hence the trailing glob.
    cy.intercept('GET', '**/gameplan.api.unread_notifications*').as('unreadCount')
    cy.visit('/g/')
    cy.wait('@unreadCount').its('response.statusCode').should('eq', 200)
    cy.get('button[aria-label="Notifications, 1 unread"]').should('exist').click()

    // ... which opens onto the mention itself
    cy.contains('Second Member mentioned you in a post')
      .should('be.visible')
      .closest('a')
      .within(() => cy.contains('Welcome thread').should('be.visible'))

    // marking everything read empties the list and drops the badge
    cy.intercept('POST', '**/gameplan.api.mark_all_notifications_as_read*').as('markAllAsRead')
    cy.button('Mark all as read').click()
    cy.dialog('button:contains("Mark all as read")').click()
    cy.wait('@markAllAsRead')

    cy.contains("You're caught up").should('be.visible')
    cy.contains('Second Member mentioned you in a post').should('not.exist')
    cy.get('button[aria-label="Notifications, 1 unread"]').should('not.exist')
    cy.get('button[aria-label="Notifications"]').should('exist')
  })

  it('shows a loading skeleton, not the empty state, while the list loads', () => {
    cy.loginAs('member')
    // Hold the list response so the in-flight window is observable.
    cy.intercept('GET', '**/api/v2/document/GP%20Notification*', (req) => {
      req.continue((res) => res.setDelay(600))
    }).as('notificationList')

    cy.visit('/g/notifications')
    cy.get('[role="status"][aria-label="Loading notification"]').should('be.visible')
    cy.contains("You're caught up").should('not.exist')

    cy.wait('@notificationList')
    cy.contains("You're caught up").should('be.visible')
    cy.get('[aria-label="Loading notification"]').should('not.exist')
  })

  it('refreshes read notifications after moderation even when the unread count stays zero', () => {
    cy.then(() =>
      cy.request('POST', '/api/method/frappe.client.insert', {
        doc: {
          doctype: 'GP Notification',
          to_user: 'member@example.com',
          from_user: 'member2@example.com',
          discussion,
          type: 'Mention',
          message: 'Previously read discussion notification',
          read: 1,
        },
      }),
    )
    cy.loginAs('member')
    cy.visit('/g/notifications')
    cy.contains('button', /^\s*Read\s*$/).click()
    cy.contains('Previously read discussion notification').should('be.visible')
    for (const action of ['hide', 'restore']) {
      cy.then(() =>
        cy.task('requestAsUser', {
          user: 'Administrator',
          path: `/api/v2/document/GP Discussion/${discussion}/method/${action}`,
          body: action === 'hide' ? { reason: 'Reviewed elsewhere' } : {},
        }),
      )
      cy.window().then((win) => {
        const app = (win.document.querySelector('#app') as any).__vue_app__
        const handlers = app.config.globalProperties.$socket.listeners(
          'gameplan:notification_count_changed',
        )
        expect(handlers, 'notification event listeners').not.to.be.empty
        handlers.forEach((handler: (payload: unknown) => void) => {
          handler({ count: 0, force_refresh: true })
          handler({ count: 0 })
        })
      })
      cy.contains('Previously read discussion notification').should(
        action === 'hide' ? 'not.exist' : 'be.visible',
      )
    }
  })
})
