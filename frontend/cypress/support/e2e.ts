// ***********************************************************
// This example support/e2e.ts is processed and
// loaded automatically before your test files.
//
// This is a great place to put global configuration and
// behavior that modifies Cypress.
//
// You can change the location of this file or turn off
// automatically serving support files with the
// 'supportFile' configuration option.
//
// You can read more here:
// https://on.cypress.io/configuration
// ***********************************************************

// Import commands using ES2015 syntax:
import './commands'
import './personas'

// "ResizeObserver loop completed with undelivered notifications" is a benign
// browser warning emitted while layout settles (e.g. after dialogs/menus open).
// It is not an app error, so don't let it fail otherwise-passing tests.
Cypress.on('uncaught:exception', (err) => {
  if (err.message.includes('ResizeObserver loop')) {
    return false
  }
})
