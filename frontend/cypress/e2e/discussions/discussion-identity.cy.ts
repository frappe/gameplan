// A discussion page must show the post its URL names, whatever was open before it.
//
// The Discussion route reuses one page component across posts, so jumping from one post
// to another (here through the command palette) walks that component through several ids.
// A shared document cache keyed by id but bound to that component's id getter used to
// follow it, and then served the last post read to the next visitor of the first one.
import { resetData } from '../../support/seed'

describe('Discussion identity', () => {
  let community: string
  let space: string
  let firstDiscussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      firstDiscussion = String(ids.discussion)
    })
    cy.then(() =>
      cy.request('POST', '/api/v2/document/GP%20Discussion', {
        title: 'Release checklist',
        content: '<p>Second post, so the page component has somewhere to go.</p>',
        project: space,
      }),
    )
    // The palette's discussion results come from the search index, not from local data.
    cy.request('POST', '/api/method/gameplan.ui_test_helpers.rebuild_search_index')
    cy.loginAs('member')
  })

  it('shows the post the URL names after jumping to another post and back', () => {
    cy.intercept('GET', '**/gameplan.command_palette.search_sqlite*').as('paletteSearch')
    cy.visit(`/g/community/${community}/space/${space}/discussion/${firstDiscussion}`)
    cy.contains('h1', 'Welcome thread').should('be.visible')

    // Jump straight to the other post: same route, same component, new id. Selected with
    // the keyboard, not a click: each result carries a relative timestamp that re-renders
    // its row every second, which detaches whatever a click was aiming at.
    openCommandPalette()
    commandPaletteInput().type('Release checklist')
    cy.wait('@paletteSearch')
    // Two rows: the discussion, and the "Search for ..." row the palette starts on. Wait
    // for both before pressing a key, or the arrow lands in a list that is still growing.
    cy.get('[role="option"]').should('have.length', 2)
    commandPaletteInput().type('{upArrow}')
    cy.contains('[role="option"]', 'Release checklist').should('have.attr', 'aria-selected', 'true')
    commandPaletteInput().type('{enter}')
    cy.contains('h1', 'Release checklist').should('be.visible')

    // Back to the first post, in-app, the way a notification or a list row opens it.
    cy.contains('a', 'Engineering').first().click()
    cy.contains('a', 'Welcome thread').click()

    cy.url().should('include', `/discussion/${firstDiscussion}/`)
    cy.contains('h1', 'Welcome thread').should('be.visible')
    cy.contains('h1', 'Release checklist').should('not.exist')
  })

  function openCommandPalette() {
    cy.get('body').then(($body) => {
      $body[0].dispatchEvent(
        new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true }),
      )
    })
    commandPaletteInput().should('be.visible')
  }

  function commandPaletteInput() {
    return cy.get('input[role="combobox"][aria-controls="command-palette-listbox"]')
  }
})
