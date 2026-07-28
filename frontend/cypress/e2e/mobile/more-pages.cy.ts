import { resetData } from '../../support/seed'

describe('Mobile More-menu pages', () => {
  beforeEach(() => {
    cy.viewport('iphone-6')
    resetData('onboarded')
    cy.loginAs('member')
  })

  // Land on the More menu directly; the Home→You tab path is covered by
  // mobile/community-home.cy.ts and is flaky to re-drive here.
  const openMore = () => {
    cy.visit('/g/more')
    cy.url().should('include', '/more')
  }

  // The mobile header is the only *visible* <h1> on each page (the desktop
  // PageHeader uses Breadcrumbs). The :visible filter also skips the hidden
  // mobile header that teleports alongside the desktop one at wide widths.
  it('opens each workspace page with a mobile header and backs out to More', () => {
    // "Manage" is intentionally omitted: it now opens the Communities Settings
    // dialog (an overlay) rather than a mobile page with a Back-to-More header.
    // That flow is covered separately below.
    const pages = [
      { label: 'Bookmarks', path: '/bookmarks', title: 'Bookmarks' },
      { label: 'Pages', path: '/pages', title: 'Pages' },
      { label: 'Tasks', path: '/tasks', title: 'Tasks' },
      { label: 'People', path: '/people', title: 'People' },
      { label: 'Drafts', path: '/drafts', title: 'Drafts' },
    ]

    pages.forEach(({ label, path, title }) => {
      openMore()
      cy.button(label).scrollIntoView().click()
      cy.url().should('include', path)
      cy.contains('h1:visible', title)

      // Shared MobileBackButton (aria-label "Back") returns to the More menu.
      cy.iconButton('Back').click()
      cy.url().should('include', '/more')
    })
  })

  it('relocates header actions into the mobile header slots', () => {
    // Runs as admin: the People page's Invite action is admin-only, so a member
    // never sees that particular relocated header action.
    cy.loginAs('admin')

    openMore()
    cy.button('Tasks').click()
    cy.iconButton('Add task').should('be.visible')

    openMore()
    cy.button('People').click()
    cy.iconButton('Invite').should('be.visible')

    openMore()
    cy.button('Pages').click()
    // Sort control moves into the right slot of the mobile header (default order
    // is "Date Updated").
    cy.get('header').filter(':visible').contains('Date Updated').should('be.visible')
  })

  it('does not offer community management from the mobile More menu', () => {
    // Community settings is desktop-only; the mobile More menu must not expose a
    // "Manage" entry.
    openMore()
    cy.button('People').should('be.visible')
    cy.contains('button', 'Manage').should('not.exist')
  })

  it('keeps the desktop header and hides the mobile back button at wide widths', () => {
    cy.viewport(1280, 800)
    cy.visit('/g/bookmarks')

    // Desktop PageHeader (Breadcrumbs) is the visible header…
    cy.get('header').filter(':visible').should('contain.text', 'Bookmarks')
    // …while the mobile-only header h1 + back button are present but not shown.
    cy.contains('h1:visible', 'Bookmarks').should('not.exist')
    cy.get('button[aria-label="Back"]:visible').should('not.exist')
  })
})
