import { resetData } from '../../support/seed'

// A poll written into a discussion's opening post, the same block and card as a poll in
// a comment. The server creates the poll when the post is saved and keeps it out of the
// thread, so the card shows once, inside the post.
describe('Poll in the opening post', () => {
  let community: string
  let space: string
  let discussion: string

  it('writes a poll into a new discussion, publishes it, and another member votes', () => {
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
    })
    cy.loginAs('member')
    let pollSaved = false
    cy.intercept(/\/api\/v2\/document\/GP%20Draft/, (req) => {
      if (JSON.stringify(req.body ?? {}).includes('Pizza')) pollSaved = true
    })
    cy.then(() => cy.visit(`/g/community/${community}/new-discussion`))

    cy.get('textarea[placeholder="Title"]').type('Team lunch')
    cy.get('[contenteditable=true]').click().type('Friday is on the company.')
    cy.contains('button', 'Select space').click()
    cy.get('[role="option"]').contains('General').click()

    cy.iconButton('Poll').click()
    // An unfinished poll blocks publishing, as it blocks submitting a comment.
    cy.button('Publish').should('be.disabled')
    labelledInput('Question').should('be.focused').type('Lunch?')
    cy.get('input[placeholder="Option 1"]').type('Pizza')
    cy.get('input[placeholder="Option 2"]').type('Salad')
    // A post holds one poll.
    cy.iconButton('Poll').should('be.disabled')
    cy.wrap(null).should(() => expect(pollSaved, 'poll autosaved').to.be.true)

    cy.intercept('GET', '/api/v2/document/GP%20Discussion/*').as('getDiscussion')
    cy.button('Publish').click()
    cy.url().should('match', /\/discussion\/\d+/)
    cy.wait('@getDiscussion').then(({ response }) => {
      discussion = String(response?.body.data.name)
      expect(response?.body.data.content).to.match(/Friday is on the company.*data-poll="\d+"/s)
    })

    // The card shows once: in the post, and not again in the thread.
    cy.contains('Lunch?').should('be.visible')
    cy.get('[data-poll-option="Pizza"]').should('have.length', 1)

    cy.intercept('POST', '/api/v2/document/GP%20Poll/*/method/submit_vote').as('submitVote')
    cy.url().then((url) => {
      cy.switchUser('secondMember')
      cy.visit(url)
    })
    pollChoice('Salad').click()
    cy.wait('@submitVote').its('request.body.option').should('equal', 'Salad')
    pollChoice('Salad').should('have.attr', 'aria-checked', 'true')
    cy.contains('1 vote').should('exist')

    // The vote is stored on the poll in the post.
    cy.reload()
    pollChoice('Salad').should('have.attr', 'aria-checked', 'true')
    cy.contains('1 vote').should('exist')
  })

  it('lets the author add a poll while editing, and asks before removing it', () => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
    })
    cy.loginAs('member')
    cy.intercept('PUT', '/api/v2/document/GP%20Discussion/*').as('savePost')
    const openPost = () =>
      cy.then(() => cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`))
    openPost()

    editPost()
    cy.button('Poll').click()
    labelledInput('Question').type('Lunch?')
    cy.get('input[placeholder="Option 1"]').type('Pizza')
    cy.get('input[placeholder="Option 2"]').type('Salad')
    cy.button('Save').click()
    cy.wait('@savePost')
    cy.get('[data-poll-option="Pizza"]').should('have.length', 1)

    // Only the author adds a poll to their post. Another member may still edit it.
    cy.switchUser('secondMember')
    openPost()
    editPost()
    cy.contains('button:visible', /^\s*Poll\s*$/).should('not.exist')
    cy.button('Discard').click()

    // Taking the poll out deletes its votes, so saving asks first.
    cy.switchUser('member')
    openPost()
    editPost()
    // The poll closes the post. Delete at the end of the line above it selects the poll,
    // and a second Delete removes it.
    cy.get('[contenteditable=true] > p').last().click().type('{moveToEnd}{del}{del}')
    cy.button('Poll').should('be.visible')
    cy.button('Save').click()
    cy.dialog('button:contains("Cancel")').click()
    cy.get('[role=dialog]').should('not.exist')
    cy.button('Save').click()
    cy.dialog('button:contains("Remove poll")').click()
    cy.wait('@savePost')
    cy.contains('Lunch?').should('not.exist')
  })
})

function editPost() {
  cy.iconButton('Discussion options').click()
  cy.get('[role=menuitem]').contains('Edit').click()
  cy.button('Save').should('be.visible')
}

function labelledInput(label: string) {
  return cy.contains('label', label).then(($label) => cy.get(`[id="${$label.attr('for')}"]`))
}

/** An answer on a single-answer poll, where the options are one radiogroup. */
function pollChoice(label: string) {
  return cy.get(`[role="radio"][aria-label="${label}"]`)
}
