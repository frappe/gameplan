import { createInvitation, resetData } from '../../support/seed'

// The invitee's side of the invitation feature: opening the invite link mints a
// user with the granted role and routes a brand-new account to password setup.
// An account that existed before the invitation is sent to the app instead.
// (The admin send-side happy path lives in member-management.cy.ts; the full
// create/accept/expire matrix lives in the backend suite test_invitations.py.)
describe('Accept invitation', () => {
  beforeEach(() => {
    resetData('onboarded')
  })

  it('mints a new member and routes them to set a password', () => {
    const email = 'invited-newcomer@example.com'

    createInvitation(email).then(({ key }) => {
      // Opening the invite link accepts the invitation and, for an account with
      // no password yet, redirects to the password-setup page.
      cy.visit(`/api/method/gameplan.api.accept_invitation?key=${key}`)
      cy.location('pathname').should('include', '/update-password')
    })

    // The invitation is now consumed and the invitee is a real Gameplan Member.
    cy.request({
      method: 'GET',
      url: '/api/method/frappe.client.get_value',
      qs: {
        doctype: 'GP Invitation',
        filters: JSON.stringify({ email }),
        fieldname: 'status',
      },
    })
      .its('body.message.status')
      .should('eq', 'Accepted')
  })

  it('accepts an invitation for an existing member and opens Gameplan', () => {
    const email = 'member@example.com'

    // The account existed before the invitation, so accepting it grants the role
    // and sends the browser to the app without signing in as that account. The
    // spec's own session opens /g.
    createInvitation(email).then(({ key }) => {
      cy.visit(`/api/method/gameplan.api.accept_invitation?key=${key}`)
      cy.location('pathname').should('match', /^\/g(?:\/|$)/)
    })

    cy.request({
      method: 'GET',
      url: '/api/method/frappe.client.get_value',
      qs: {
        doctype: 'GP Invitation',
        filters: JSON.stringify({ email }),
        fieldname: 'status',
      },
    })
      .its('body.message.status')
      .should('eq', 'Accepted')
  })
})
