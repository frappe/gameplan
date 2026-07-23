import { resetData } from '../../support/seed'

describe('Mobile community home', () => {
  let alpha: string
  let alphaSpace: string

  beforeEach(() => {
    cy.viewport('iphone-6')
    resetData('two_communities').then(({ communities, spaces }) => {
      const [firstCommunity] = communities as string[]
      const [firstSpace] = spaces as string[]
      alpha = firstCommunity
      alphaSpace = firstSpace
    })
    cy.loginAs('member')
  })

  it('opens a community feed from the mobile home', () => {
    cy.visit('/g')
    cy.url().should('include', '/home')
    cy.contains('button', 'Alpha').should('be.visible')
    cy.contains('button', 'Beta').should('be.visible')

    // Tapping a community lands directly on its All Discussions feed.
    cy.contains('button', 'Alpha').click()
    cy.url().should('include', `/community/${alpha}/discussions`)
  })

  it('switches feeds and spaces from the header sheet', () => {
    cy.visit(`/g/community/${alpha}/discussions`)

    // The header title opens the community switcher sheet, which lists this
    // community's feeds and spaces only.
    cy.contains('button', 'All Discussions').click()
    cy.scope('dialog').button('Unread').should('be.visible')
    cy.scope('dialog').button('Participating').should('be.visible')
    cy.scope('dialog').button('Alpha Space').should('be.visible')
    cy.scope('dialog').contains('button', 'Beta Space').should('not.exist')

    // Picking a feed stays within the discussions page.
    cy.scope('dialog').button('Unread').click()
    cy.url().should('include', `/community/${alpha}/discussions/unread`)

    // Picking a space from the same switcher navigates into it.
    cy.scope('header').button('Unread').click()
    cy.scope('dialog').button('Alpha Space').click()
    cy.url().should('include', `/community/${alpha}/space/${alphaSpace}`)
  })

  it('shows the global tabs in the bottom nav', () => {
    cy.visit('/g')
    cy.url().should('include', '/home')

    // Search drops the community scope: no feed or space rows in its header.
    cy.contains('[data-slot="mobile-nav-item"]', 'Search').click()
    cy.url().should('include', '/search')
    cy.contains('button', 'All discussions').should('not.exist')
    cy.contains('button', 'Alpha Space').should('not.exist')

    cy.contains('[data-slot="mobile-nav-item"]', 'You').click()
    cy.url().should('include', '/more')
    cy.contains('View profile').should('be.visible')
    cy.contains('button', 'Bookmarks').should('be.visible')
    cy.contains('button', 'People').should('be.visible')
    cy.contains('button', 'Pages').should('be.visible')
    cy.contains('button', 'Tasks').should('be.visible')
    cy.contains('button', 'Drafts').should('be.visible')
    // Community management is desktop-only; the mobile More menu has no "Manage".
    cy.contains('button', 'Manage').should('not.exist')
  })
})
