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

// Export for ES module compatibility
export {}
