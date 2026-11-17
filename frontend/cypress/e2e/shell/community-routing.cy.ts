// The community-scope routing end state:
// - `/` and `/home` resolve to community discussions, or to All Discussions when that
//   preference is on.
// - The community sidebar is visible on `/community/:communityId/*` and hidden on
//   global routes.
// - `/bookmarks` stays a global destination.
import { resetData } from '../../support/seed'

describe('Community scope routing', () => {
  let community: string

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = ids.community as string
    })
    cy.loginAs('member')
  })

  it('resolves `/` and `/home` to community discussions by default', () => {
    cy.visit('/g')
    cy.url().should('include', `/community/${community}/discussions`)

    cy.visit('/g/home')
    cy.url().should('include', `/community/${community}/discussions`)
  })

  it('resolves `/` and `/home` to All Discussions when the preference is on', () => {
    const turnOnAllDiscussions = {
      onBeforeLoad(win: Window) {
        win.localStorage.setItem('gameplan:showAllDiscussions', 'true')
      },
    }

    cy.visit('/g', turnOnAllDiscussions)
    cy.location('pathname').should('eq', '/g/discussions')

    cy.visit('/g/home', turnOnAllDiscussions)
    cy.location('pathname').should('eq', '/g/discussions')
  })

  it('shows the community sidebar on scoped routes and hides it on global ones', () => {
    cy.visit(`/g/community/${community}/discussions`)
    // Sidebar lists this community's spaces, and the page owns discussion feed tabs.
    cy.contains('a', 'General').should('be.visible')
    cy.contains('button:visible', 'All discussions').should('be.visible')

    // Global routes drop the community sidebar; its space rows are gone.
    cy.visit('/g/bookmarks')
    cy.url().should('include', '/bookmarks')
    cy.contains('a', 'General').should('not.exist')
  })

  it('keeps `/bookmarks` global', () => {
    cy.visit('/g/bookmarks')
    cy.url().should('include', '/bookmarks')
    cy.url().should('not.include', '/community/')
  })
})
