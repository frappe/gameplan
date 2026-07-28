// Test personas seeded by the backend reset helper
// (gameplan.ui_test_helpers.reset). All personas share the password "admin".

export const personas = {
  admin: {
    email: 'Administrator',
    password: 'admin',
    displayName: 'Administrator',
  },
  member: {
    email: 'member@example.com',
    password: 'admin',
    displayName: 'Member',
  },
  secondMember: {
    email: 'member2@example.com',
    password: 'admin',
    displayName: 'Second Member',
  },
  guest: {
    email: 'guest@example.com',
    password: 'admin',
    displayName: 'Guest',
  },
  outsider: {
    email: 'outsider@example.com',
    password: 'admin',
    displayName: 'Outsider',
  },
} as const

export type PersonaName = keyof typeof personas

declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Custom command to login as a seeded test persona
       * @param persona - One of the persona keys (admin, member, secondMember, guest, outsider)
       */
      loginAs(persona: PersonaName): Chainable<void>

      /**
       * Custom command to switch the browser session to another persona mid-test,
       * after a page has already been loaded as someone else.
       * @param persona - One of the persona keys (admin, member, secondMember, guest, outsider)
       */
      switchUser(persona: PersonaName): Chainable<void>
    }
  }
}

Cypress.Commands.add('loginAs', (persona: PersonaName) => {
  const { email, password } = personas[persona]
  cy.request({
    url: '/api/method/login',
    method: 'POST',
    body: { usr: email, pwd: password },
  })
})

/**
 * Switch personas after a page has already been loaded as someone else.
 *
 * A bare `cy.loginAs` is only safe before the first `cy.visit`. Frappe re-sets the
 * `sid` cookie on *every* response for the session that request ran under
 * (`CookieManager.init_cookies`), so any request the old page still has in flight —
 * a feed refresh, an unread update, a realtime poll — can land after the login and
 * hand the previous user's cookie straight back. The next visit then boots as the
 * old user, and the test fails on whatever it asserts about the new one.
 *
 * So: unload the page first (which aborts its pending requests), then log in, then
 * only continue once the server itself names the acting user.
 */
Cypress.Commands.add('switchUser', (persona: PersonaName) => {
  cy.window({ log: false }).then((win) => {
    win.location.href = 'about:blank'
  })
  cy.window({ log: false }).its('location.href').should('eq', 'about:blank')

  // Drop the old session's cookie outright, so a login that somehow fails shows up
  // as a guest error instead of quietly passing as the previous user.
  cy.clearCookies()
  cy.loginAs(persona)
  cy.request('/api/method/frappe.auth.get_logged_user')
    .its('body.message')
    .should('eq', personas[persona].email)
})

// Export for ES module compatibility
export {}
