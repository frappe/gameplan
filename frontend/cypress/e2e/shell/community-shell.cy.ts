// The shell IA: the rail community switcher, scoped discussions URLs, and the
// global bookmarks destination living outside any community.
import { resetData } from '../../support/seed'

describe('Community shell IA', () => {
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

  it('lands on a scoped discussions URL with feed tabs', () => {
    cy.visit('/g')
    cy.url().should('match', /\/community\/[^/]+\/discussions/)
    cy.contains('button:visible', 'All Discussions').should('be.visible')
    cy.contains('button:visible', 'Unread').should('be.visible')
    cy.contains('button:visible', 'Participating').should('be.visible')
  })

  it('switches communities from the rail switcher', () => {
    cy.visit(`/g/community/${alpha}/discussions`)
    cy.url().should('include', `/community/${alpha}/discussions`)
    cy.contains('a', 'Alpha Space').should('be.visible')

    switchCommunity('Beta')
    cy.url().should('include', `/community/${beta}/discussions`)
    cy.contains('a', 'Beta Space').should('be.visible')
  })

  it('keeps bookmarks a global destination outside any community', () => {
    cy.visit('/g/bookmarks')
    cy.url().should('include', '/bookmarks')
    cy.url().should('not.include', '/community/')
  })
})
