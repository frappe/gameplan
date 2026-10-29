import { resetData } from '../../support/seed'

// The scenario seeds two discussions that both mention "roadmap": "Public roadmap" in
// the community's General space, and "Secret thread" in the private "Secret Plans"
// space. `member` is a member of the private space, `member2` is not — so one search
// term separates who may see what.
describe('Search privacy', () => {
  const term = 'roadmap'

  beforeEach(() => {
    resetData('private_space_with_guest')
    // The SQLite index is built on demand, not by the seed.
    cy.request('POST', '/api/method/gameplan.ui_test_helpers.rebuild_search_index')
  })

  it('shows private-space search results only to space members', () => {
    cy.loginAs('member')
    cy.visit(`/g/search?q=${term}`)
    cy.contains('Public roadmap').should('be.visible')
    cy.contains('Secret thread').should('be.visible')

    cy.loginAs('secondMember')
    cy.visit(`/g/search?q=${term}`)
    cy.contains('Public roadmap').should('be.visible')
    cy.contains('Secret thread').should('not.exist')
  })

  it('keeps Guest search and author filters usable without exposing account emails', () => {
    cy.loginAs('guest')
    cy.intercept('GET', '**/gameplan.api.search_sqlite*').as('search')
    cy.visit(`/g/search?q=${term}`)
    cy.wait('@search').then(({ response }) => {
      expect(response?.statusCode).to.eq(200)
      expect(JSON.stringify(response?.body)).not.to.include('member@example.com')
    })
    cy.contains('Secret thread').should('be.visible')
    cy.contains('Public roadmap').should('not.exist')
    cy.button('Author').click()
    cy.contains('[role="option"]', 'Member').click()
    cy.get('body').type('{esc}')
    cy.wait('@search').then(({ response }) => {
      expect(response?.statusCode).to.eq(200)
      expect(JSON.stringify(response?.body)).not.to.include('member@example.com')
    })
    cy.contains('Secret thread').should('be.visible').click()
    cy.contains('h1', 'Secret thread').should('be.visible')
  })
})
