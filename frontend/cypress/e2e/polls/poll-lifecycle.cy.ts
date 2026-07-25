import { resetData } from '../../support/seed'

// One flow: the poll a member creates is the poll they vote in and then stop, so
// there is nothing to seed beyond the discussion it lives in.
describe('Poll lifecycle', () => {
  let community: string
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
    })
    cy.loginAs('member')
  })

  it('creates a poll, votes in it, sees the tally, and stops it', () => {
    cy.intercept('GET', `/api/v2/document/GP%20Discussion/${discussion}`).as('getDiscussion')
    // Poll.vue still drives its doc methods through the legacy run_doc_method endpoint,
    // so alias each call by the method it carries rather than by URL.
    cy.intercept('POST', '/api/method/run_doc_method*', (req) => {
      if (req.body?.method) req.alias = req.body.method
    })
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)
    cy.wait('@getDiscussion')

    cy.intercept({ method: 'POST', url: '/api/v2/document/GP%20Poll', times: 1 }).as('createPoll')
    cy.button('Add a comment').click()
    cy.button('Poll').click()

    // The question input is only reachable through its <label for>, the way a
    // screen reader would find it.
    labelledInput('Question').type('Ship on Friday?')
    cy.get('input[placeholder="Option 1"]').type('Yes')
    cy.get('input[placeholder="Option 2"]').type('No')
    cy.button('Submit').click()
    cy.wait('@createPoll').its('response.body.data.title').should('equal', 'Ship on Friday?')

    cy.contains('Ship on Friday?').should('be.visible')
    cy.contains('0 votes').should('exist')

    // vote
    cy.contains('button', 'Yes').click()
    cy.wait('@submit_vote')

    // the tally updates for the voter: one vote, all of it on "Yes"
    cy.contains('1 vote').should('exist')
    cy.contains('button', 'Yes').contains('(100%)').should('exist')
    cy.contains('button', 'No').contains('(0%)').should('exist')

    // stop the poll
    cy.button('Stop Poll').click()
    cy.dialog('button:contains("Stop")').click()
    cy.wait('@stop_poll')

    cy.contains('Ended').should('exist')
    cy.contains('button', 'Stop Poll').should('not.exist')
    cy.contains('button', 'Yes').should('be.disabled')
  })
})

function labelledInput(label: string) {
  return cy.contains('label', label).then(($label) => cy.get(`[id="${$label.attr('for')}"]`))
}
