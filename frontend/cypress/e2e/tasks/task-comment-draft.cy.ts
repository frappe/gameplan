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

  it('holds the reply composer closed until the draft has loaded', () => {
    cy.visit(`/g/community/${community}/space/${space}/tasks`)

    cy.intercept('POST', '/api/v2/document/GP%20Task').as('createTask')
    cy.button('Add new').click()
    cy.contains('[role=dialog] label', 'Title').parent().find('input').type('Draft race task')
    cy.button('Create').click()
    cy.wait('@createTask')

    cy.intercept('POST', '/api/v2/document/GP%20Task/*/method/track_visit').as('trackVisit')
    cy.contains('a', 'Draft race task').click()
    cy.wait('@trackVisit')

    // Hold the draft lookup open so the load window is wide enough to act in. Matched by
    // regex: the method path segment is dotted (…gp_draft.gp_draft.find_my_draft), which
    // a minimatch glob can't target cleanly.
    cy.intercept(/find_my_draft/, (req) => {
      req.continue((res) => res.setDelay(2000))
    }).as('findDraft')

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
})
