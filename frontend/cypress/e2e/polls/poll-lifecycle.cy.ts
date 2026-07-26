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

  // A poll is a post like any other, so it carries reactions too. Reacting to it used
  // to blow up: GP Poll rendered the Reactions widget without mixing in HasReactions,
  // so the `react` doc-method the widget posts to did not exist.
  it('reacts to a poll, and the reaction survives a reload', () => {
    const EMOJI = '👍'
    let poll: string

    // The poll belongs to member2 — this spec is about reacting to it, not about
    // composing one (the flow above owns that). Created before the first `cy.visit`,
    // which is what keeps `loginAs` safe and the request free of a session CSRF token.
    cy.loginAs('secondMember')
    cy.request({
      method: 'POST',
      url: '/api/v2/document/GP%20Poll',
      body: {
        title: 'Ship on Friday?',
        discussion,
        options: [{ title: 'Yes' }, { title: 'No' }],
      },
    }).then((response) => {
      poll = String(response.body.data.name)
    })
    cy.loginAs('member')

    cy.intercept('POST', '/api/v2/document/GP%20Poll/*/method/react').as('reactToPoll')
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)
    cy.contains('Ship on Friday?').should('be.visible')

    // Two reaction widgets are on the page, in document order: the discussion's own
    // above the timeline, the poll's inside it. Nothing else is seeded in between.
    cy.get('button[aria-label="Add a reaction"]').last().click()
    cy.get(`button:contains("${EMOJI}"):visible`).click()
    cy.wait('@reactToPoll')
      .its('request.url')
      .should((url: string) => expect(url).to.contain(poll))

    // The pill separates emoji and count with a non-breaking space, so match on a
    // regex (\s covers U+00A0) rather than a literal space.
    const pill = new RegExp(`${EMOJI}\\s*1`)
    // Only the poll was reacted to, so exactly one pill exists on the page.
    const assertPollReactionShown = () =>
      cy
        .get('button')
        .filter((_, el) => pill.test(el.textContent ?? ''))
        .should('have.length', 1)

    assertPollReactionShown()

    cy.reload()
    cy.contains('Ship on Friday?').should('be.visible')
    assertPollReactionShown()
  })
})

function labelledInput(label: string) {
  return cy.contains('label', label).then(($label) => cy.get(`[id="${$label.attr('for')}"]`))
}
