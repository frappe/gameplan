import { resetData } from '../../support/seed'

type AppSocket = {
  nsp: string
  io: { engine: { emit: (event: string, data: string) => void } }
}

// One flow: the poll a member creates is the poll they vote in and then stop, so
// there is nothing to seed beyond the discussion it lives in.
describe('Poll lifecycle', () => {
  let community: string
  let space: string
  let discussion: string
  let discussionSlug: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
      discussionSlug = String(ids.discussion_slug)
    })
    cy.loginAs('member')
  })

  it('creates a multiple-answer poll, toggles answers, receives a live tally, and stops it', () => {
    let poll: string

    cy.intercept('GET', `/api/v2/document/GP%20Discussion/${discussion}`).as('getDiscussion')
    cy.intercept('POST', '/api/v2/document/GP%20Poll/*/method/submit_vote').as('submitVote')
    cy.intercept('POST', '/api/v2/document/GP%20Poll/*/method/retract_vote').as('retractVote')
    cy.intercept('POST', '/api/v2/document/GP%20Poll/*/method/stop_poll').as('stopPoll')
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
    labelledCheckbox('Multiple answers').check()
    labelledCheckbox('Anonymous').should('be.disabled')
    cy.button('Submit').click()
    cy.wait('@createPoll').then(({ response }) => {
      expect(response?.body.data.title).to.equal('Ship on Friday?')
    })

    cy.contains('Ship on Friday?').should('be.visible')
    cy.contains('0 answers from 0 people').should('exist')

    // Each answer is a real checkbox: it is independently keyboard reachable,
    // exposes its checked state, and posts the option through the v2 doc method.
    pollAnswer('Yes').focus().type(' ')
    cy.wait('@submitVote').then(({ request }) => {
      expect(request.body.option).to.equal('Yes')
      const match = request.url.match(/GP(?:%20| )Poll\/([^/]+)\/method/)
      expect(match, 'poll method URL').to.not.be.null
      poll = decodeURIComponent(match![1])
    })
    pollAnswer('No').check()
    cy.wait('@submitVote').its('request.body.option').should('equal', 'No')

    cy.contains('2 answers from 1 person').should('exist')
    pollAnswer('Yes').should('be.checked')
    pollAnswer('No').should('be.checked')
    // A percentage is a share of the people who voted, not of the answer rows, so the
    // one voter who picked both options puts both at 100%. On "select all that apply"
    // the shares are meant to add up to more than 100%.
    assertShare('Yes', '100%')
    assertShare('No', '100%')

    // Deselecting one checkbox retracts only that option.
    pollAnswer('Yes').uncheck()
    cy.wait('@retractVote').its('request.body.option').should('equal', 'Yes')
    cy.contains('1 answer from 1 person').should('exist')
    pollAnswer('Yes').should('not.be.checked')
    pollAnswer('No').should('be.checked')
    assertShare('Yes', '0%')
    assertShare('No', '100%')

    // A second user's answer reaches this already-open poll through the document
    // update listener. The local bench cannot authenticate demo-site sockets, so
    // deliver the server frame through the page's real socket.io decoder.
    cy.then(() => {
      cy.task('requestAsUser', {
        user: 'member2@example.com',
        path: `/api/v2/document/GP Poll/${poll}/method/submit_vote`,
        body: { option: 'Yes' },
      })
    })
    cy.contains('1 answer from 1 person').should('exist')
    cy.then(() => {
      deliverSocketEvent('doc_update', {
        doctype: 'GP Poll',
        name: poll,
      })
    })
    cy.contains('2 answers from 2 people').should('exist')

    // Moderators can stop polls they do not own. Switch sessions safely before
    // exercising the global-admin affordance and backend gate.
    cy.switchUser('admin')
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)
    cy.contains('Ship on Friday?').should('be.visible')
    pollAnswer('Yes').should('be.enabled')
    cy.button('Stop Poll').click()
    cy.dialog('button:contains("Stop")').click()
    cy.wait('@stopPoll')

    cy.contains('Ended').should('exist')
    cy.contains('button', 'Stop Poll').should('not.exist')
    pollAnswer('Yes').should('be.disabled')
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

    // The poll author receives a usable bell entry: it names the poll and routes
    // back to the discussion with the poll query that scrolls the timeline to it.
    cy.switchUser('secondMember')
    cy.intercept('GET', '**/gameplan.api.unread_notifications*').as('unreadCount')
    cy.visit('/g/')
    cy.wait('@unreadCount')
    cy.get('button[aria-label="Notifications, 1 unread"]').click()
    cy.contains('1 person reacted to your post').should('be.visible')
    cy.contains('Ship on Friday?').should('be.visible')
    cy.contains('1 person reacted to your post').click()
    cy.location('pathname').should(
      'eq',
      `/g/community/${community}/space/${space}/discussion/${discussion}/${discussionSlug}`,
    )
    cy.location('search').should((search) => {
      expect(search).to.equal(`?poll=${poll}`)
    })
    cy.contains('Ship on Friday?').should('be.visible')
  })

  it('keeps a poll readable but inert after its space is archived', () => {
    cy.request({
      method: 'POST',
      url: '/api/v2/document/GP%20Poll',
      body: {
        title: 'Archived poll',
        discussion,
        options: [{ title: 'Yes' }, { title: 'No' }],
      },
    })
    cy.loginAs('admin')
    cy.request('POST', `/api/v2/document/GP%20Project/${space}/method/archive`)
    cy.loginAs('member')

    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)
    cy.contains('Archived poll').should('be.visible')
    cy.contains('button', 'Stop Poll').should('not.exist')
    pollAnswer('Yes').should('be.disabled')

    cy.iconButton('Poll Options').click()
    cy.get('[role="menuitem"]:visible').contains('Show results').should('be.visible')
    cy.get('[role="menuitem"]:visible').contains('Copy link').should('be.visible')
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Retract vote')
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Delete')
    cy.get('[role="menuitem"]:visible').contains('Show results').click()
    cy.contains('[role="dialog"]', 'Poll results').should('be.visible')
    cy.get('body').type('{esc}')

    cy.selectDropdownOption('Poll Options', 'Copy link')
    cy.contains('Copied to clipboard').should('be.visible')
  })
})

function labelledInput(label: string) {
  return cy.contains('label', label).then(($label) => cy.get(`[id="${$label.attr('for')}"]`))
}

function labelledCheckbox(label: string) {
  return cy
    .get('label')
    .filter((_, element) => element.textContent?.trim() === label)
    .should('have.length', 1)
    .then(($label) => cy.get(`input[type="checkbox"][id="${$label.attr('for')}"]`))
}

function pollAnswer(label: string) {
  return cy.get(`input[type="checkbox"][aria-label="${label}"]`)
}

/** The option's whole row: the checkbox, its share of the vote, and the bar behind them. */
function pollAnswerRow(label: string) {
  return cy.get(`[data-poll-option="${label}"]`)
}

/**
 * Assert an option's share exactly. A substring match would not do: `contains('0%')`
 * also matches "100%", so the assertion that a retracted option drops to 0% could not
 * fail for the bug it exists to catch.
 */
function assertShare(label: string, share: string) {
  pollAnswerRow(label)
    .contains('span', /^\s*\d+%\s*$/)
    .invoke('text')
    .then((text) => expect(text.trim()).to.equal(share))
}

function deliverSocketEvent(event: string, payload: unknown) {
  cy.window({ log: false })
    .its('document')
    .then((doc) => {
      const app = (doc.querySelector('#app') as { __vue_app__?: any } | null)?.__vue_app__
      const socket = app?.config?.globalProperties?.$socket as AppSocket | undefined
      expect(socket, 'app socket').to.exist
      socket!.io.engine.emit('data', `2${socket!.nsp},${JSON.stringify([event, payload])}`)
    })
}
