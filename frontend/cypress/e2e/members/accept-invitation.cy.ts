import { createInvitation, resetData } from '../../support/seed'

// The invitee's side of the invitation feature: opening the invite link mints a
// user with the granted role and routes a brand-new account to password setup.
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
      method: 'POST',
      url: '/api/method/frappe.client.get_value',
      body: { doctype: 'GP Invitation', filters: { email }, fieldname: 'status' },
    })
      .its('body.message.status')
      .should('eq', 'Accepted')
  })
})
