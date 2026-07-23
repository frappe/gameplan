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
})
