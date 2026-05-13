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
       * Custom command to scope queries to predefined root elements
       * @param scope - Named scope key
       */
      scope(scope: 'dialog' | 'sidebar' | 'body' | 'header'): Chainable<JQuery<HTMLElement>>

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

      /**
       * Custom command to select an option from a dropdown menu
       * @param dropdownName - Aria-label of the dropdown button
       * @param option - Option text to select from the dropdown
       */
      selectDropdownOption(dropdownName: string, option: string): Chainable<void>
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

const scopeSelectors = {
  dialog: '[role="dialog"]',
  sidebar: '[data-sidebar]',
  body: '#scrollContainer',
  header: 'header',
} as const

type ScopeKey = keyof typeof scopeSelectors

Cypress.Commands.add('scope', (scope: ScopeKey) => {
  const selector = scopeSelectors[scope]
  if (!selector) {
    throw new Error(
      `Unknown scope "${scope}". Use one of: ${Object.keys(scopeSelectors).join(', ')}`,
    )
  }
  return cy.get(selector)
})

Cypress.Commands.add('button', { prevSubject: 'optional' }, (subject, text: string) => {
  const root = subject ? cy.wrap(subject) : cy
  return root.contains('button:visible', text)
})

Cypress.Commands.add('combobox', { prevSubject: 'optional' }, (subject, placeholder: string) => {
  const inputSelector = `input[placeholder="${placeholder}"][role="combobox"]`
  const root = subject ? cy.wrap(subject) : cy.get('body')
  return root.then(($root) => {
    const $input = $root.find(`${inputSelector}:visible`)
    if ($input.length) return cy.wrap($input.first())
    // Button-mode trigger: the search input lives inside the popover and only
    // exists once the trigger is clicked. Return the trigger button so callers
    // can `.click()` it; use `selectCombobox` to also type + select an option.
    return cy.wrap($root).contains('button[aria-haspopup="listbox"]', placeholder)
  })
})

Cypress.Commands.add('iconButton', { prevSubject: 'optional' }, (subject, text: string) => {
  const selector = `button[aria-label="${text}"]:visible`
  return subject ? cy.wrap(subject).find(selector) : cy.get(selector)
})

Cypress.Commands.add('dialog', (selector: string) => {
  return cy.get(`[role=dialog] ${selector}`)
})

Cypress.Commands.add('selectCombobox', (placeholder: string, option: string) => {
  const inputSelector = `input[placeholder="${placeholder}"][role="combobox"]:visible`
  const buttonSelector = `button[aria-haspopup="listbox"]`

  // Retry until either an input-mode trigger or a button-mode trigger is present.
  // Dialog-hosted comboboxes mount via reka-ui's DialogPortal after a tick, so a
  // one-shot DOM check can miss them.
  cy.get('body').should(($body) => {
    const hasInput = $body.find(inputSelector).length > 0
    const hasButton = $body
      .find(buttonSelector)
      .filter((_, el) => Cypress.$(el).is(':visible') && el.textContent?.includes(placeholder))
      .length > 0
    expect(hasInput || hasButton, `trigger for "${placeholder}" mounted`).to.be.true
  })

  cy.get('body').then(($body) => {
    if (!$body.find(inputSelector).length) {
      // Button-mode trigger: open the popover so the search input mounts.
      cy.contains(buttonSelector, placeholder).click()
    }
  })

  cy.get(inputSelector).click().clear().type(`${option}`)

  // Select the option from the dropdown
  cy.get('[role="option"]').contains(option).click()
})

Cypress.Commands.add('selectDropdownOption', (dropdownName: string, option: string) => {
  cy.get(`button[aria-haspopup=menu][aria-label="${dropdownName}"]`).click()
  cy.get(`[role="menuitem"]:contains("${option}"):visible`).click()
})

// Export for ES module compatibility
export {}
