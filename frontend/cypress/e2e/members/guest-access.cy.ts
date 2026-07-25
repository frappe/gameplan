// A guest's whole world in the app: exactly the spaces they were granted, and inside
// them a participant — they can comment and react, but never edit, pin, close or move
// somebody else's post.
//
// The rules themselves are specced on the backend
// (gameplan/tests/features/test_guest_participation.py and
// permissions/test_guest_access.py). This spec only proves the UI honours them, so it
// stays one walk through the guest's scoped view — no permission matrix here.
import { resetData } from '../../support/seed'

const EMOJI = '👍'

describe('Guest access', () => {
  let community: string
  let privateSpace: string

  beforeEach(() => {
    // "Secret Plans" is private and granted to the guest; the community's General space
    // (holding "Public roadmap") is not, so it must stay entirely out of the guest's view.
    resetData('private_space_with_guest').then((ids) => {
      community = String(ids.community)
      privateSpace = String(ids.private_space)
    })
    cy.loginAs('guest')
  })

  it('scopes a guest to the granted space and lets them participate in it', () => {
    cy.intercept('POST', '/api/v2/document/GP%20Comment').as('comment')
    cy.intercept('POST', '/api/v2/document/GP%20Discussion/*/method/react').as('react')

    // The guest never joined the community, but the granted space puts them inside it.
    cy.visit('/g')
    cy.url().should('include', `/community/${community}/`)

    // Only the granted space is reachable: it is in the sidebar, General is not, and
    // neither is the post General holds.
    cy.contains('a', 'Secret Plans').should('be.visible')
    cy.contains('a', 'General').should('not.exist')
    cy.contains('Public roadmap').should('not.exist')

    // Open the member's discussion from the granted space.
    cy.contains('a', 'Secret Plans').click()
    cy.url().should('include', `/space/${privateSpace}/`)
    cy.contains('a', 'Secret thread').should('be.visible').click()
    cy.contains('h1', 'Secret thread').should('be.visible')

    // Participation 1: comment on the member's post.
    cy.button('Add a comment').click()
    cy.get('[contenteditable=true]').should('be.visible').click().type('A guest can reply here')
    cy.button('Submit').click()
    cy.wait('@comment')
      .its('response.body.data')
      .then((comment: { name: string }) => {
        cy.get(`div[data-id="${comment.name}"]`).should('exist')
      })

    // Participation 2: react to the member's post. Reactions render one widget per post,
    // in document order, so the first "Add a reaction" button is the discussion's own.
    cy.get('button[aria-label="Add a reaction"]').first().click()
    cy.get(`button:contains("${EMOJI}"):visible`).click()
    cy.wait('@react')
    // The pill separates emoji and count with a non-breaking space, so match on a regex.
    cy.contains('button', new RegExp(`${EMOJI}\\s*1`)).should('exist')

    // ...but nothing that changes the member's post itself. The menu still opens (Copy
    // link proves it rendered), it just carries none of the owner-only actions.
    cy.get('body').type('{esc}')
    cy.get('button[aria-haspopup=menu][aria-label="Discussion Options"]').click()
    cy.get('[role="menuitem"]:contains("Copy link"):visible').should('exist')
    for (const action of ['Edit', 'Pin discussion', 'Close discussion', 'Move to']) {
      cy.get(`[role="menuitem"]:contains("${action}")`).should('not.exist')
    }
  })
})
