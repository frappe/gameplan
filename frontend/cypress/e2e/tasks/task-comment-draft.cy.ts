import { resetData } from '../../support/seed'

// The task reply composer auto-saves as a comment draft, and that draft is fetched when
// the page opens. Until it arrives the composer must not accept input: anything written
// in that window is thrown away when the draft lands, and an image pasted there is
// uploaded to the server and then silently dropped from the document.
describe('Task comment draft', () => {
  let community: string
  let space: string

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
    })
    cy.loginAs('member')
  })

  // Open a task and land on its detail page, ready for the comment composer.
  const openTask = (title: string) => {
    cy.visit(`/g/community/${community}/space/${space}/tasks`)

    cy.intercept('POST', '/api/v2/document/GP%20Task').as('createTask')
    cy.button('Add new').click()
    cy.contains('[role=dialog] label', 'Title').parent().find('input').type(title)
    cy.button('Create').click()
    cy.wait('@createTask')

    cy.intercept('POST', '/api/v2/document/GP%20Task/*/method/track_visit').as('trackVisit')
    cy.contains('a', title).click()
    cy.wait('@trackVisit')
  }

  // Hold the draft lookup open so the load window is wide enough to act in. Matched by
  // regex: the method path segment is dotted (…gp_draft.gp_draft.find_my_draft), which
  // a minimatch glob can't target cleanly.
  const stallDraftLookup = (ms: number) => {
    cy.intercept(/find_my_draft/, (req) => {
      req.continue((res) => res.setDelay(ms))
    }).as('findDraft')
  }

  it('holds the reply composer closed until the draft has loaded', () => {
    openTask('Draft race task')
    stallDraftLookup(2000)

    cy.reload()
    cy.button('Add a comment').click()

    // Loading: the composer says so and refuses input.
    cy.contains('[role="status"]', 'Loading draft…').should('be.visible')
    cy.get('[contenteditable]').last().should('have.attr', 'contenteditable', 'false')

    // Loaded: it opens, and what is typed into it stays.
    cy.wait('@findDraft')
    cy.contains('[role="status"]', 'Loading draft…').should('not.exist')
    cy.get('[contenteditable]')
      .last()
      .should('have.attr', 'contenteditable', 'true')
      .click()
      .type('Reply written after the draft loaded.')
    cy.contains('Reply written after the draft loaded.').should('exist')
  })

  // The gate above is only safe because it ends. A lookup that never settles — a stalled
  // fetch, an IndexedDB request blocked by another tab — used to leave the composer inert
  // for good, with no way to reply at all.
  it('gives up on a lookup that does not land and opens the composer anyway', () => {
    openTask('Draft deadline task')
    // Well past the deadline, and past the assertion window below: the composer has to
    // open on its own timer, not because the response finally arrived.
    stallDraftLookup(20000)

    cy.reload()
    cy.button('Add a comment').click()
    cy.contains('[role="status"]', 'Loading draft…').should('be.visible')

    // Past the 8s deadline the composer opens blank and editable, well before the response.
    cy.contains('[role="status"]', 'Loading draft…', { timeout: 12000 }).should('not.exist')
    cy.get('[contenteditable]')
      .last()
      .should('have.attr', 'contenteditable', 'true')
      .click()
      .type('Reply written while the lookup hung.')

    // And the late response does not reach in and overwrite what was typed meanwhile.
    cy.wait('@findDraft')
    cy.contains('Reply written while the lookup hung.').should('exist')
  })
})
