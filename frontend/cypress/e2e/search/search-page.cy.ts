import { resetData } from '../../support/seed'

describe('Search page', () => {
  beforeEach(() => {
    resetData('search_page')
    cy.request('POST', '/api/method/gameplan.ui_test_helpers.rebuild_search_index')
    cy.loginAs('member')

    cy.intercept('GET', '/api/v2/method/gameplan.api.search_sqlite*').as('search')
    cy.intercept('GET', '/api/v2/method/gameplan.api.get_search_filter_options*').as(
      'filterOptions',
    )
  })

  it('searches and narrows results with every filter', () => {
    cy.visit('/g/search')
    cy.wait('@filterOptions').its('response.statusCode').should('eq', 200)

    cy.get('input[placeholder="Search or press / to focus"]').type('roadmap{enter}')
    cy.wait('@search').its('response.statusCode').should('eq', 200)
    cy.contains('6 matches').should('be.visible')

    selectFilter('Author', 'Member')
    cy.contains('5 matches').should('contain', '1 filter(s) applied')
    cy.contains('Design roadmap').should('not.exist')

    selectFilter('Community', 'Acme')
    cy.contains('4 matches').should('contain', '2 filter(s) applied')
    cy.contains('Beta roadmap').should('not.exist')

    selectFilter('Space', 'Engineering')
    cy.contains('3 matches').should('contain', '3 filter(s) applied')
    cy.contains('General roadmap').should('not.exist')

    selectFilter('Type', 'Discussion')
    cy.contains('2 matches').should('contain', '4 filter(s) applied')
    cy.contains('Engineering roadmap page').should('not.exist')

    selectFilter('Tags', 'launch')
    cy.contains('1 matches').should('contain', '5 filter(s) applied')
    cy.contains('Untagged roadmap').should('not.exist')
    cy.contains('Launch roadmap').should('be.visible').click()
    cy.url().should('match', /\/g\/community\/acme\/space\/\d+\/discussion\/\d+\/launch-roadmap$/)
  })

  function selectFilter(placeholder: string, option: string) {
    cy.button(placeholder).click()
    cy.get(`input[placeholder="${placeholder}"][role="combobox"]:visible`).type(option)
    cy.get('[role="option"]')
      .contains(new RegExp(`^${option}$`, 'i'))
      .click()
    cy.wait('@search').its('response.statusCode').should('eq', 200)
  }
})
