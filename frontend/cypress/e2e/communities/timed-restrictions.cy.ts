import { resetData } from '../../support/seed'

function duration(label: string) {
  cy.get('[role="dialog"]')
    .contains('button', /Until manually lifted|Keep current expiry/)
    .click()
  cy.contains('[role="option"]', new RegExp(`^${label}$`)).click()
}

function confirm(reason: string, action = 'Save restriction') {
  cy.get('[role="dialog"] textarea').type(reason)
  cy.get('[role="dialog"]').contains('button', action).click()
  cy.get('[role="dialog"]').should('not.exist')
}

describe('Timed moderation restrictions', () => {
  it('applies and lifts a timed Community ban with a reason and timezone', () => {
    resetData('space_with_discussion').then(({ community }) => {
      cy.visit(`/g/moderation?community=${community}&tab=bans`)
      cy.get('input[placeholder="Name or email"]').type('Member')
      cy.contains('[role="option"]', /^M?Member$/).click()
      cy.contains('button', 'Ban from Community').click()
      duration('1 hour')
      cy.get('[role="dialog"]').contains('Times shown in').should('be.visible')
      confirm('One hour participation restriction')
      cy.contains('One hour participation restriction').should('be.visible')
      cy.contains('button', 'Change').should('be.visible')
      cy.contains('button', 'Lift ban').click()
      cy.get('[role="dialog"]').contains('button', 'Lift restriction').should('be.disabled')
      confirm('Appeal accepted', 'Lift restriction')
      cy.contains('No active Community bans.').should('be.visible')
      cy.contains('History').click()
      cy.contains('Appeal accepted').should('be.visible')
    })
  })

  it('manages whole-site suspensions and retains history after lifting', () => {
    resetData('space_with_discussion')
    cy.visit('/g/moderation?scope=site')
    cy.contains('Applies to the entire Frappe site').should('be.visible')
    cy.get('input[placeholder="Name or email"]').type('Outsider')
    cy.contains('[role="option"]', /Outsider/).click()
    cy.contains('button', /^Suspend account$/).click()
    duration('1 day')
    confirm('Temporary account suspension')
    cy.contains('Temporary account suspension').should('be.visible')
    cy.contains('button', 'Lift suspension').click()
    confirm('Account access restored', 'Lift restriction')
    cy.contains('No active account suspensions.').should('be.visible')
    cy.get('input[placeholder="Name or email"]').type('Outsider')
    cy.contains('[role="option"]', /Outsider/).click()
    cy.contains('button', /Selected user history|View history/).click()
    cy.get('[role="dialog"]').contains('Account access restored').should('be.visible')
  })

  it('keeps account suspension controls hidden from Community staff', () => {
    resetData('space_with_discussion').then(({ community }) => {
      cy.request('POST', `/api/v2/document/GP Team/${community}/method/set_member_moderator`, {
        user: 'member2@example.com',
        is_moderator: 1,
      })
      cy.switchUser('secondMember')
      cy.visit(`/g/moderation?community=${community}&scope=site`)
      cy.contains('Community bans').should('be.visible')
      cy.contains('button', 'Account suspensions').should('not.exist')
      cy.contains('button', 'Suspend account').should('not.exist')
    })
  })
  it('keeps paged users mounted and searches beyond the loaded page', () => {
    resetData('onboarded')
    cy.intercept('POST', '**/gameplan.restriction_queries.candidates', (req) => {
      const { query = '', after = '' } = req.body
      const start = after ? Number(after.replace(/\D/g, '')) : 0
      const items =
        query && query !== 'Scale'
          ? [
              {
                name: 'remote-49999@example.invalid',
                full_name: 'Remote user outside the loaded page',
              },
            ]
          : Array.from({ length: 20 }, (_, index) => ({
              name: `scale-${String(start + index + 1).padStart(5, '0')}@example.invalid`,
              full_name: `Scale person ${start + index + 1}`,
            }))
      const result = {
        items,
        has_more: !query || query === 'Scale',
        next_cursor: query && query !== 'Scale' ? '' : `scale-${start + 20}@example.invalid`,
      }
      req.alias =
        query === 'Scale'
          ? after
            ? 'scaleNext'
            : 'scaleFirst'
          : query === 'al'
            ? 'slowCandidates'
            : query
              ? 'remoteCandidates'
              : after
                ? 'nextCandidates'
                : 'firstCandidates'
      req.reply({ delay: query === 'al' ? 800 : 150, body: { message: result, data: result } })
    })
    cy.visit('/g/moderation?scope=site')
    cy.get('input[placeholder="Name or email"]').click()
    cy.wait('@firstCandidates')
    cy.get('[role="option"]').should('have.length', 20)
    cy.get('[data-reka-combobox-viewport]').scrollTo('bottom')
    cy.wait('@nextCandidates')
    cy.get('[role="option"]').should('have.length', 40)
    cy.get('[data-reka-combobox-viewport]').invoke('scrollTop').should('be.greaterThan', 0)
    cy.contains('button', 'Load more users').click()
    cy.wait('@nextCandidates')
    cy.get('[role="option"]').should('have.length', 60)
    cy.get('input[placeholder="Name or email"]').type('Scale')
    cy.wait('@scaleFirst')
    cy.get('[role="option"]').should('have.length', 20)
    cy.get('[data-reka-combobox-viewport]').scrollTo('bottom')
    cy.wait('@scaleNext')
    cy.get('[role="option"]').should('have.length', 40)
    cy.get('[data-reka-combobox-viewport]').invoke('scrollTop').should('be.greaterThan', 100)
    cy.get('input[placeholder="Name or email"]').clear().type('far')
    cy.wait('@remoteCandidates').its('request.body').should('include', { query: 'far', after: '' })
    cy.contains('[role="option"]', 'Remote user outside the loaded page').should('be.visible')
    cy.get('input[placeholder="Name or email"]').clear().type('al')
    cy.get('[data-slot="loading"]').should('be.visible')
    cy.get('input[placeholder="Name or email"]').type('{backspace}')
    cy.contains('Type one more character to search the site.').should('be.visible')
    cy.wait('@slowCandidates')
    cy.get('[data-slot="loading"]').should('not.exist')
    cy.contains('Type one more character to search the site.').should('be.visible')
  })
})
