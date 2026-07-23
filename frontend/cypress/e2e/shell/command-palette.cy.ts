// The command palette: how it opens, how the active row behaves while a query is
// typed, and how results are grouped under their parent heading.
import { resetData } from '../../support/seed'

describe('Command palette', () => {
  let community: string
  let communityTitle: string
  let generalSpace: string

  beforeEach(() => {
    resetData('unread_discussion').then((seeded) => {
      community = String(seeded.community)
      generalSpace = String(seeded.space)
    })
    // Two tests let the real search endpoint answer. Rebuilding the index ties its
    // results to the world we just seeded instead of whatever was indexed before.
    cy.request('POST', '/api/method/gameplan.ui_test_helpers.rebuild_search_index')
    // Spaces are grouped under their community's *title*, and the seed yields ids,
    // so read the title back instead of repeating a literal in the assertions.
    cy.then(() => cy.request(`/api/v2/document/GP%20Team/${community}`)).then((response) => {
      communityTitle = String(response.body.data.title)
    })
    cy.clearLocalStorage()
    cy.loginAs('member')
  })

  it('ignores stale server search responses and keeps the active row stable', () => {
    // The palette debounces its server search, so typing "mar" and then "k" fires two
    // requests. The first one belongs to a query the user has already moved past, and
    // its answer must never reach the list.
    //
    // The stub decides the order, not the clock: the stale reply is held open until
    // this test releases it, so "mark" always lands first and "mar" always lands last.
    let releaseStaleResponse: (() => void) | undefined

    cy.intercept('GET', '**/gameplan.command_palette.search_sqlite*', (req) => {
      const query = String(req.query.query ?? '')

      if (query === 'mar') {
        req.alias = 'staleSearch'
        return new Promise<void>((resolve) => {
          releaseStaleResponse = resolve
        }).then(() => {
          req.reply({
            body: {
              data: [
                {
                  title: 'Discussions',
                  items: [searchResultItem('Old Mar Discussion', generalSpace)],
                },
              ],
            },
          })
        })
      }

      if (query === 'mark') {
        req.alias = 'freshSearch'
        req.reply({
          body: {
            data: [
              {
                title: 'Discussions',
                items: [searchResultItem('New Mark Discussion', generalSpace)],
              },
            ],
          },
        })
        return
      }

      req.reply({ body: { data: [] } })
    })

    visitCommunityDiscussions()
    openCommandPalette()

    commandPaletteInput().type('mar')
    // Only type the "k" once the stale request is actually in flight; typing sooner
    // would restart the debounce and there would be no stale response to ignore.
    cy.wrap(null, { log: false }).should(() => {
      expect(releaseStaleResponse, 'stale search request in flight').to.be.a('function')
    })

    commandPaletteInput().type('k')
    commandPaletteInput().invoke('attr', 'aria-activedescendant').as('activeRow')

    cy.wait('@freshSearch')
    cy.get('[role="listbox"]').should('contain', 'New Mark Discussion')

    cy.then(() => releaseStaleResponse?.())
    cy.wait('@staleSearch')

    cy.get('[role="listbox"]').should('contain', 'New Mark Discussion')
    cy.get('[role="listbox"]').should('not.contain', 'Old Mar Discussion')
    cy.get<string>('@activeRow').then((activeRow) => {
      commandPaletteInput().should('have.attr', 'aria-activedescendant', activeRow)
    })
  })

  it('opens with the first row active even when the mouse is centered', () => {
    visitCommunityDiscussions()
    cy.get('body').trigger('mousemove', { clientX: 640, clientY: 250 })

    openCommandPalette()

    assertFirstOptionActive()
  })

  it('keeps the first result active while typing a query', () => {
    visitCommunityDiscussions()
    openCommandPalette()
    commandPaletteInput().type('{downArrow}')
    cy.get('[role="option"]').then(($options) => {
      cy.get('[role="option"][aria-selected="true"]').should('have.attr', 'id', $options[1].id)
    })

    commandPaletteInput().type(communityTitle)

    assertFirstOptionActive()
    cy.get('[role="option"][aria-selected="true"]').should(
      'not.contain',
      `Search for "${communityTitle}"`,
    )
  })

  it('keeps the mark-all-as-read dialog open when selected with Enter', () => {
    visitCommunityDiscussions()
    openCommandPalette()
    commandPaletteInput().type('read all')
    cy.contains('[role="option"]', 'Mark all as read').should('have.attr', 'aria-selected', 'true')

    commandPaletteInput().type('{enter}')

    cy.contains('[role="dialog"]', 'Mark all as read').should('be.visible')
    commandPaletteInput().should('not.exist')
  })

  it('groups Settings tabs and spaces under their parent headings', () => {
    visitCommunityDiscussions()
    openCommandPalette()
    commandPaletteInput().type('settings')

    resultGroup('Settings').within(() => {
      cy.contains('[role="option"]', 'Profile').should('exist')
      cy.contains('[role="option"]', 'Preferences').should('exist')
      cy.contains('[role="option"]', 'Notifications').should('exist')
    })

    // Every space carries its community title in its search text, so searching the
    // community name matches both seeded spaces and leaves the grouping to assert.
    commandPaletteInput().clear().type(communityTitle)
    cy.get('[role="option"][aria-selected="true"]').should(
      'not.contain',
      `Search for "${communityTitle}"`,
    )
    resultGroup(communityTitle).within(() => {
      cy.contains('[role="option"]', 'General').should('exist')
      cy.contains('[role="option"]', 'Product').should('exist')
      // The community itself sits under "Communities", never inside its own group.
      cy.contains('[role="option"]', communityTitle).should('not.exist')
    })
    cy.contains('[role="option"]', `Search for "${communityTitle}"`).should('exist')
  })

  function visitCommunityDiscussions() {
    cy.visit(`/g/community/${community}/discussions`)
    cy.contains('button:visible', 'All Discussions').should('be.visible')
  }

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

  function resultGroup(label: string) {
    return cy.get('[role="group"]').filter((_, element) => {
      const labelId = element.getAttribute('aria-labelledby')
      return labelId ? Cypress.$(`#${labelId}`).text().trim() === label : false
    })
  }

  function assertFirstOptionActive() {
    cy.get('[role="option"]').then(($options) => {
      cy.get('[role="option"][aria-selected="true"]').should('have.attr', 'id', $options[0].id)
    })
  }

  function searchResultItem(title: string, project: string) {
    return {
      author: 'member@example.com',
      content: '',
      doctype: 'GP Discussion',
      id: title,
      modified: Math.floor(Date.now() / 1000),
      name: title.toLowerCase().replace(/\W+/g, '-'),
      project,
      score: 1,
      team: community,
      title,
    }
  }
})
