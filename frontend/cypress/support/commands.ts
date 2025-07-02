// ***********************************************
// This file contains custom Cypress commands
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************

// Declare custom command types
declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Custom command to login with email and password
       * @param email - User email (optional, defaults to Administrator)
       * @param password - User password (optional, defaults to admin password from config)
       */
      login(email?: string, password?: string): Chainable<void>

      /**
       * Custom command to get a button by text content
       * @param text - Button text to search for
       */
      button(text: string): Chainable<JQuery<HTMLElement>>

      /**
       * Custom command to get a combobox by placeholder
       * @param placeholder - Placeholder text of the combobox input
       */
      combobox(placeholder: string): Chainable<JQuery<HTMLElement>>

      /**
       * Custom command to get a button by aria-label
       * @param text - Aria-label text to search for
       */
      iconButton(text: string): Chainable<JQuery<HTMLElement>>

      /**
       * Custom command to get elements within a dialog
       * @param selector - CSS selector within the dialog
       */
      dialog(selector: string): Chainable<JQuery<HTMLElement>>

      /**
       * Custom command to select an option from a combobox
       * @param placeholder - Placeholder text of the combobox input
       * @param option - Option text to select
       */
      selectCombobox(placeholder: string, option: string): Chainable<void>
    }
  }
}

Cypress.Commands.add('login', (email?: string, password: string = 'admin') => {
  if (!email) {
    email = (Cypress.config() as any).testUser || 'Administrator'
  }
  cy.request({
    url: '/api/method/login',
    method: 'POST',
    body: { usr: email, pwd: password },
  })
})

Cypress.Commands.add('button', (text: string) => {
  return cy.get(`button:contains("${text}"):visible`)
})

Cypress.Commands.add('combobox', (placeholder: string) => {
  return cy.get(`input[placeholder="${placeholder}"][role="combobox"]`)
})

Cypress.Commands.add('iconButton', (text: string) => {
  return cy.get(`button[aria-label="${text}"]:visible`)
})

Cypress.Commands.add('dialog', (selector: string) => {
  return cy.get(`[role=dialog] ${selector}`)
})

Cypress.Commands.add('selectCombobox', (placeholder: string, option: string) => {
  // Click the combobox input to open dropdown
  cy.get(`input[placeholder="${placeholder}"]`).click()

  // Select the option from the dropdown
  cy.get('[role="option"]').contains(option).click()
})

// Export for ES module compatibility
export {}
