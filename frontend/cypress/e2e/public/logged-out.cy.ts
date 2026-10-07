import { resetData, type SeedIds } from '../../support/seed'

// Reading a public space without signing in, and the controls that decide what is public.
//
// Needs `gameplan_public_access_enabled: 1` in the site config. CI sets it in
// .github/helper/install.sh when the UI workflows pass GAMEPLAN_PUBLIC_ACCESS. Without it
// nothing is public and every logged-out visit sends you to log in, so the first test
// checks the switch before anything else fails in a confusing way.

const PERSONA_EMAILS = /[\w.+-]+@example\.com/

describe('Public spaces, logged out', () => {
  let ids: SeedIds

  beforeEach(() => {
    resetData('public_space').then((seeded) => {
      ids = seeded
    })
    // resetData signs in as Administrator; a logged-out visitor has no session at all.
    cy.clearCookies()
  })

  function threadPath() {
    return `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`
  }

  function expectLoginRedirect(path: string) {
    cy.visit(path)
    cy.location('pathname').should('eq', '/login')
    cy.location('search').should('include', encodeURIComponent(path))
  }

  it('reads a public thread, with authors by name and no email anywhere', () => {
    cy.intercept('GET', '**/gameplan.public_lists.comments*').as('comments')
    cy.intercept('GET', '**/gameplan.public_lists.polls*').as('polls')
    cy.intercept('GET', '**/api/v2/document/GP%20Discussion/*').as('discussion')

    cy.visit(threadPath())
    cy.window().its('public_access_enabled').should('eq', true)

    cy.contains('h1', 'Welcome to Open Source').should('be.visible')
    cy.contains('Ask @Second Member anything.').should('be.visible')
    cy.contains('Glad to be here.').should('be.visible')
    // Authors are shown by name, looked up by profile handle.
    cy.contains('Member').should('be.visible')
    cy.contains('Second Member').should('be.visible')
    // Reactions are totals; the poll shows results, never voters.
    cy.contains('button', '🎉').should('contain.text', '1')
    cy.contains('Ship it this week?').should('be.visible')
    cy.contains('100%').should('be.visible')
    cy.button('Log in to vote').should('be.visible')
    cy.contains('Join the conversation').scrollIntoView().should('be.visible')

    // Hovering reaction in anonymous mode must not show any tooltip popover
    cy.contains('button', '🎉').trigger('mouseenter')
    cy.get('[role="tooltip"]').should('not.exist')

    // User hover cards revealing member activity must not appear for anonymous visitors
    cy.contains('@Second Member').trigger('mouseenter')
    cy.contains('in the last 3 months').should('not.exist')
    cy.contains('@Second Member').click()
    cy.location('pathname').should('eq', threadPath())

    // Author names are plain text, not links to profile pages
    cy.contains('Second Member').closest('a').should('not.exist')

    // Nothing that reached the browser names anyone by email.
    for (const alias of ['@discussion', '@comments', '@polls']) {
      cy.wait(alias).then(({ response }) => {
        expect(response?.statusCode).to.eq(200)
        expect(JSON.stringify(response?.body)).not.to.match(PERSONA_EMAILS)
      })
    }
    cy.document().its('documentElement.outerHTML').should('not.match', PERSONA_EMAILS)

    // There is nothing a visitor can do here except log in.
    cy.get('[contenteditable="true"]').should('not.exist')
    cy.button('Log in').first().click()
    cy.location('pathname').should('eq', '/login')
    cy.location('search').should('include', encodeURIComponent(threadPath()))
  })

  it('shows rail and sidebar with public community and spaces, theme toggle, and hides forbidden actions', () => {
    cy.visit(threadPath())

    // AppRail is present
    cy.get('button[aria-label="Account menu"]').should('be.visible')

    // Rail contains the public community listing item
    cy.get('button[aria-label="Open Source"]').should('be.visible')

    // Search is public; member-only shortcuts stay hidden.
    cy.get('button[aria-label="Search"]').should('be.visible')
    cy.contains('Notifications').should('not.exist')
    cy.contains('Drafts').should('not.exist')

    // AppSidebar is present with community title and public space
    cy.get('.gameplan-desktop-shell').within(() => {
      cy.contains('Open Source').should('be.visible')
      cy.contains('Spaces').should('be.visible')
      cy.contains('Announcements').should('be.visible')
      // Private spaces are hidden
      cy.contains('Core Team').should('not.exist')
      // Member-only space controls are hidden
      cy.get('button[aria-label="New space"]').should('not.exist')
      cy.get('button[aria-label="Sort spaces"]').should('not.exist')
    })

    // Account menu has dark mode toggle and login
    cy.get('button[aria-label="Account menu"]').click()
    cy.contains('Toggle theme').should('be.visible')
    cy.contains('Log in').should('be.visible')
    // Member-only items are hidden
    cy.contains('My Profile').should('not.exist')
    cy.contains('Bookmarks').should('not.exist')
    cy.contains('Settings').should('not.exist')

    // Theme toggle works for anonymous visitor
    cy.contains('Toggle theme').click()
    cy.contains('Dark Mode').click()
    cy.get('html').should('have.attr', 'data-theme', 'dark')
  })

  it('keeps public spaces visible when the browser remembers hiding inactive spaces', () => {
    cy.visit(`/g/community/${ids.community}/discussions`, {
      onBeforeLoad(win) {
        win.localStorage.setItem('gameplan:hideInactiveSpaces', 'true')
      },
    })
    cy.get('.gameplan-desktop-shell').contains('Announcements').should('be.visible')
  })

  it('lets a mobile visitor browse public spaces without member-only feeds', () => {
    cy.viewport(390, 844)
    cy.visit(`/g/community/${ids.community}/discussions`)
    cy.get('header:visible').contains('button', 'Log in').should('be.visible')
    cy.get('header:visible button').contains('Discussions').click()
    cy.get('[role="dialog"]').within(() => {
      cy.contains('Announcements').should('be.visible')
      cy.contains('Unread').should('not.exist')
      cy.contains('Participating').should('not.exist')
      cy.contains('Core Team').should('not.exist')
      cy.contains('Announcements').click()
    })
    cy.location('pathname').should('include', `/space/${ids.space}`)
    cy.get('header:visible button').contains('Announcements').click()
    cy.get('[role="dialog"]').contains('All discussions').should('be.visible')
  })

  it('lists the public space and opens a thread from it', () => {
    cy.visit(`/g/community/${ids.community}/space/${ids.space}/discussions`)
    cy.get('.gameplan-desktop-shell').contains('Announcements').should('be.visible')
    cy.contains('Members-only thread').should('not.exist')
    cy.contains('a', 'Welcome to Open Source').click()
    cy.location('pathname').should('include', `/discussion/${ids.discussion}`)
    cy.contains('Glad to be here.').should('be.visible')
  })

  it('opens the public community as a forum without exposing non-public spaces', () => {
    cy.visit(`/g/community/${ids.community}/discussions`)
    cy.get('.gameplan-desktop-shell').contains('Open Source').should('be.visible')
    cy.get('.gameplan-desktop-shell header:visible').contains('Discussions').should('be.visible')
    cy.contains('Welcome to Open Source').should('be.visible')
    cy.contains('Announcements').should('be.visible')
    cy.contains('General').should('not.exist')
    cy.contains('Core Team').should('not.exist')

    cy.contains('a', 'Welcome to Open Source').click()
    cy.location('pathname').should('include', `/discussion/${ids.discussion}`)
  })

  it('sends a visitor to log in for anything that is not public', () => {
    expectLoginRedirect(`/g/community/${ids.community}/space/${ids.general_space}/discussions`)
    expectLoginRedirect(`/g/community/${ids.community}/space/${ids.private_space}/discussions`)
    expectLoginRedirect(
      `/g/community/${ids.community}/space/${ids.general_space}/discussion/${ids.hidden_discussion}`,
    )
    expectLoginRedirect('/g/people')
  })
})

describe('Changing a tier', () => {
  let ids: SeedIds

  beforeEach(() => {
    resetData('public_space').then((seeded) => {
      ids = seeded
    })
  })

  // The access dialog underneath has radios of its own.
  function tiers() {
    return cy.get('[role="radiogroup"][aria-label^="Visibility of"] [role="radio"]')
  }

  function openVisibilityDialog(space: string) {
    cy.visit(`/g/community/${ids.community}/space/${space}/discussions`)
    cy.selectDropdownOption('Space actions', 'Manage access')
    cy.scope('dialog').find('button[aria-label="Change visibility"]').click()
  }

  it('lets a Gameplan Admin publish a space, after showing what that exposes', () => {
    cy.loginAs('admin')
    cy.intercept('POST', '**/get_visibility_change_impact').as('impact')
    cy.intercept('POST', '**/set_visibility').as('setVisibility')

    openVisibilityDialog(ids.general_space as string)
    tiers().contains('Anonymous').click()
    cy.wait('@impact').its('response.statusCode').should('eq', 200)
    // The Gameplan Guest is the one person who could not read a General space before.
    cy.scope('dialog').should('contain.text', '1 person will be able to read it.')
    cy.scope('dialog').should(
      'contain.text',
      '1 discussion becomes readable by anyone on the web, without signing in.',
    )
    cy.contains('[role="dialog"] button:visible', 'Change visibility').click()
    cy.wait('@setVisibility').its('response.statusCode').should('eq', 200)

    cy.clearCookies()
    cy.visit(`/g/community/${ids.community}/space/${ids.general_space}/discussions`)
    cy.contains('a', 'Members-only thread').should('be.visible')
  })

  it('shows a community admin the control, but disabled', () => {
    cy.loginAs('member')
    openVisibilityDialog(ids.space as string)
    cy.scope('dialog').should('contain.text', 'Only Gameplan Admins can change visibility.')
    tiers()
      .should('have.length', 3)
      .each(($radio) => cy.wrap($radio).should('be.disabled'))
    cy.contains('[role="dialog"] button:visible', 'Change visibility').should('be.disabled')
  })
})
