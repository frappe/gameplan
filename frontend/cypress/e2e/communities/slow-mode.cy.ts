import { resetData, type SeedIds } from '../../support/seed'

const path = (ids: SeedIds) =>
  `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}`

describe('Discussion slow mode', () => {
  it('retains drafts while waiting, rejects direct posts, and refreshes settings on focus', () => {
    resetData('space_with_discussion').then((ids) => {
      cy.visit(path(ids))
      cy.selectDropdownOption('Discussion Options', 'Slow mode')
      cy.get('[role="dialog"] [role="combobox"]').click()
      cy.contains('[role="option"]', '30 seconds').click()
      cy.get('[role="dialog"]').contains('button', 'Save slow mode').should('be.disabled')
      cy.get('[role="dialog"] textarea').type('Give everyone time to read')
      cy.get('[role="dialog"]').contains('button', 'Save slow mode').click()
      cy.contains('Slow mode updated.').should('be.visible')
      cy.switchUser('member')
      cy.visit(path(ids))
      cy.contains('button', 'Add a comment').click()
      cy.window()
        .then((win) =>
          cy.request({
            method: 'POST',
            url: '/api/v2/document/GP Comment',
            failOnStatusCode: false,
            headers: { 'X-Frappe-CSRF-Token': (win as any).csrf_token },
            body: {
              reference_doctype: 'GP Discussion',
              reference_name: ids.discussion,
              content: '',
            },
          }),
        )
        .its('status')
        .should('eq', 417)
      cy.get('[contenteditable=true]').click().type('First slow-mode reply')
      cy.contains('button:visible', /^\s*Submit\s*$/).click()
      cy.get('[data-id]').contains('First slow-mode reply').should('be.visible')
      cy.get('[data-testid="slow-mode-status"]').should('contain.text', 'reply again in')
      cy.contains('button', 'Add a comment').click()
      cy.get('[contenteditable=true]').click().type('Keep this draft while waiting')
      cy.contains('button:visible', /^\s*Submit\s*$/).should('be.disabled')
      cy.window()
        .then((win) =>
          cy.request({
            method: 'POST',
            url: '/api/v2/document/GP Comment',
            failOnStatusCode: false,
            headers: { 'X-Frappe-CSRF-Token': (win as any).csrf_token },
            body: {
              reference_doctype: 'GP Discussion',
              reference_name: ids.discussion,
              content: 'Direct bypass',
            },
          }),
        )
        .its('status')
        .should('eq', 429)
      cy.get('[contenteditable=true]').should('contain.text', 'Keep this draft while waiting')
      cy.task('requestAsUser', {
        user: 'Administrator',
        method: 'POST',
        path: '/api/method/gameplan.slow_mode.set_mode',
        body: {
          discussion: String(ids.discussion),
          seconds: 0,
          expected_seconds: 30,
          reason: 'Conversation settled',
        },
      })
      cy.window().then((win) => win.dispatchEvent(new Event('focus')))
      cy.get('[data-testid="slow-mode-status"]').should('not.exist')
      cy.contains('button:visible', /^\s*Submit\s*$/)
        .should('not.be.disabled')
        .click()
      cy.get('[data-id]').contains('Keep this draft while waiting').should('be.visible')
    })
  })

  it('records setting changes in history and preserves Reports and Approvals tabs', () => {
    resetData('space_with_discussion').then((ids) => {
      cy.request('POST', '/api/method/gameplan.slow_mode.set_mode', {
        discussion: String(ids.discussion),
        seconds: 60,
        expected_seconds: 0,
        reason: 'Thoughtful discussion',
      })
      cy.visit(
        `/g/community/${ids.community}/moderation?tab=history&kind=discussion&target=${ids.discussion}`,
      )
      cy.contains('Slow Mode Changed').should('be.visible')
      cy.contains('Off → 1 minute').should('be.visible')
      cy.contains('Thoughtful discussion').should('be.visible')
      cy.contains('button', /^\s*Reports\s*$/).click()
      cy.contains('No pending reports.').should('be.visible')
      cy.contains('button', /^\s*Approvals\s*$/).click()
      cy.contains('No pending submissions.').should('be.visible')
      cy.switchUser('member')
      cy.visit(path(ids))
      cy.get('button[aria-label="Discussion Options"]').click()
      cy.contains('[role="menuitem"]', /^Slow mode$/).should('not.exist')
    })
  })
})
