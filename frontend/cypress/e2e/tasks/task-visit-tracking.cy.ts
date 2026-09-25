// Opening a second task without leaving the task page must still mark it visited.
//
// The task routes reuse one page component across tasks, so its setup runs once. The
// visit tracker has to follow the id the route names; anything registered on the shared
// document entry that setup happened to see stays on the first task for ever.
import { resetData } from '../../support/seed'

describe('Task visit tracking', () => {
  let community: string
  let space: string
  let secondTask: string

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
    })
    // Titles share no word, so one palette query can name exactly one of them. Both need a
    // description: the search indexer skips a document whose content field is empty, and an
    // unindexed task never reaches the palette.
    cy.then(() => {
      cy.request('POST', '/api/v2/document/GP%20Task', {
        title: 'Draft the changelog',
        description: '<p>Collect the merged pull requests.</p>',
        project: space,
      })
      cy.request('POST', '/api/v2/document/GP%20Task', {
        title: 'Rotate the certificates',
        description: '<p>Replace the expiring keys.</p>',
        project: space,
      }).then((response) => {
        secondTask = String(response.body.data.name)
      })
    })
    // The palette's task results come from the search index, not from local data.
    cy.request('POST', '/api/method/gameplan.ui_test_helpers.rebuild_search_index')
    cy.loginAs('member')
  })

  it('tracks the visit to a task opened from the command palette', () => {
    cy.intercept('POST', '/api/v2/document/GP%20Task/*/method/track_visit').as('trackVisit')
    cy.intercept('GET', '**/gameplan.command_palette.search_sqlite*').as('paletteSearch')

    cy.visit(`/g/community/${community}/space/${space}/tasks`)
    cy.contains('a', 'Draft the changelog').click()
    cy.wait('@trackVisit')

    // Jump straight to the other task: same route, same component, new id. Selected with
    // the keyboard, not a click: each result carries a relative timestamp that re-renders
    // its row every second, which detaches whatever a click was aiming at.
    openCommandPalette()
    commandPaletteInput().type('Rotate')
    cy.wait('@paletteSearch')
    // Two rows: the task, and the "Search for ..." row the palette starts on. Wait for both
    // before pressing a key, or the arrow lands in a list that is still growing.
    cy.get('[role="option"]').should('have.length', 2)
    commandPaletteInput().type('{upArrow}')
    cy.contains('[role="option"]', 'Rotate the certificates').should(
      'have.attr',
      'aria-selected',
      'true',
    )
    commandPaletteInput().type('{enter}')

    cy.get('input[placeholder="Title"]').should('have.value', 'Rotate the certificates')
    cy.wait('@trackVisit')
      .its('request.url')
      .should('include', `/GP%20Task/${secondTask}/method/track_visit`)
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
