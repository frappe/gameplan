// index.html paints <html> before the app loads. Overscrolling shows that color behind the
// app, so it has to follow every theme switch, not only the theme the page loaded with.
import { resetData } from '../../support/seed'

const pageBackground = () => cy.document().its('documentElement.style.backgroundColor')

function chooseTheme(label: string) {
  cy.get('button[aria-haspopup=menu][aria-label^="Account menu"]').click()
  cy.contains('[role="menuitem"]', 'Toggle theme').click()
  cy.contains('[role="menuitem"]', label).click()
  cy.get('[role="menu"]').should('not.exist')
}

describe('Theme', () => {
  it('repaints the page background behind the app when the theme changes', () => {
    resetData('onboarded')
    cy.loginAs('member')
    cy.visit('/g', { onBeforeLoad: (win) => win.localStorage.setItem('theme', 'light') })
    cy.url().should('include', '/discussions')
    pageBackground().should('eq', 'rgb(255, 255, 255)')

    chooseTheme('Dark Mode')
    cy.document().its('documentElement').should('have.attr', 'data-theme', 'dark')
    pageBackground().should('eq', 'rgb(23, 23, 23)')

    chooseTheme('Light Mode')
    pageBackground().should('eq', 'rgb(255, 255, 255)')
  })
})
