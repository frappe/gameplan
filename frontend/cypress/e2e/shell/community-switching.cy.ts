// Canonical `/community/:communityId/discussions` routing, the rail community
// switcher persisting the deliberate choice, and deep links NOT overwriting the
// persisted home community.
//
// The persisted choice lives in localStorage, so this spec deliberately never
// calls `cy.clearLocalStorage()`: surviving a `cy.visit` is the thing under test.
import { resetData } from '../../support/seed'

describe('Community switching', () => {
  let alpha: string
  let beta: string

  beforeEach(() => {
    resetData('two_communities').then(({ communities = [] }) => {
      ;[alpha, beta] = communities
    })
    cy.loginAs('member')
  })

  // The rail lists each community as a direct button; its aria-label is the
  // community title, suffixed with an unread count when unread posts exist.
  // `two_communities` seeds no discussions, so the plain title always matches.
  function switchCommunity(title: string) {
    cy.get(`button[aria-label="${title}"]:visible`).first().click()
  }

  it('lands on a canonical community discussions URL', () => {
    cy.visit('/g')
    cy.url().should('match', /\/community\/[^/]+\/discussions/)
  })

  it('switches communities from the rail and persists the choice across reload', () => {
    // Start scoped to the first community.
    cy.visit(`/g/community/${alpha}/discussions`)
    cy.url().should('include', `/community/${alpha}/discussions`)

    switchCommunity('Beta')
    cy.url().should('include', `/community/${beta}/discussions`)

    // A deliberate switch persists, so a fresh `/g` visit reopens the chosen community.
    cy.visit('/g')
    cy.url().should('include', `/community/${beta}/discussions`)
  })

  it('does not change the persisted home community when following a deep link', () => {
    // Deliberately switch to the second community so it becomes the persisted home.
    cy.visit(`/g/community/${alpha}/discussions`)
    switchCommunity('Beta')
    cy.visit('/g')
    cy.url().should('include', `/community/${beta}/discussions`)

    // Follow a deep link into the other community (e.g. a shared/notification link).
    cy.visit(`/g/community/${alpha}/discussions`)
    cy.url().should('include', `/community/${alpha}/discussions`)

    // Returning home should still resolve to the deliberately selected community.
    cy.visit('/g')
    cy.url().should('include', `/community/${beta}/discussions`)
  })
})
