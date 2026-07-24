import { resetData } from '../../support/seed'

// Member-management coverage: the admin happy path for inviting a member
// (gameplan.api.invite_by_email), plus the authorization boundary in the UI.
//
// Boundary note: the global user-management surfaces are admin-only in the UI.
// SettingsDialog registers the "Users" tab (which holds the invite flow) only for
// global admins, and the People page hides its Invite buttons for non-admins. So the
// non-admin test below asserts those controls are ABSENT, not merely rejected.
// Server-side `require_admin()` is the real enforcement and is covered by the backend
// suite — hiding the UI just stops non-admins from reaching controls that would 403.
describe('Member management', () => {
  let community: string

  beforeEach(() => {
    resetData('onboarded').then(({ community: seededCommunity }) => {
      community = seededCommunity as string
    })
  })

  // Opens the global Settings dialog via the sidebar app dropdown. For admins it
  // opens on the first tab (Profile).
  function openSettings() {
    cy.visit(`/g/community/${community}/discussions`)
    cy.contains('button', 'Gameplan').click()
    cy.contains('[role="menuitem"]', 'Settings').click()
    // The dialog title is a visually-hidden (sr-only) accessible label, so assert
    // presence rather than visibility.
    cy.scope('dialog').contains('h1', 'Settings').should('exist')
  }

  it('invites a member by email', () => {
    cy.loginAs('admin')
    cy.intercept('POST', '**/gameplan.api.invite_by_email').as('invite')
    openSettings()
    // Invites live on the admin-only "Users" tab, behind an "Invite" button that
    // opens the InvitePeople dialog.
    //
    // Activate the tab by keyboard, not click: the tab list is a reka-ui Tabs whose
    // trigger activates on `mousedown`. Cypress fires `pointerdown` first, and the
    // frappe-ui DialogOverlay's `@pointerdown.left.prevent` cancels it, which makes
    // Cypress suppress the synthetic `mousedown` the trigger needs — so a `.click()`
    // silently fails to switch tabs. Real users are unaffected (a native mousedown
    // still fires), and this is the same upstream frappe-ui overlay bug tracked in
    // tasks/task-actions.cy.ts. Enter is a legitimate real activation path and works
    // both now and after the frappe-ui fix lands.
    cy.scope('dialog').contains('button', 'Users').focus().type('{enter}')
    cy.scope('dialog').contains('button', 'Invite').click()

    // :visible — the Profile tab's Bio textarea stays mounted (hidden) in the
    // Settings dialog after switching tabs (unmount-on-hide=false).
    cy.scope('dialog').find('textarea:visible').type('newteammate@example.com')
    cy.button('Send invitation').click()
    cy.wait('@invite').its('response.statusCode').should('eq', 200)

    // On success the new invite shows in "Pending Invites". The Member role is
    // labelled "User" in the UI.
    cy.scope('dialog').contains('newteammate@example.com').should('be.visible')
    cy.scope('dialog').contains('(User)').should('be.visible')
  })

  it('hides global member-management controls from non-admins', () => {
    cy.loginAs('member')

    // Settings opens, but the admin-only tabs (Users, Emojis) are not registered
    // for members — only universal surfaces like "Update Password" remain.
    openSettings()
    cy.scope('dialog').contains('button', 'Users').should('not.exist')
    cy.scope('dialog').contains('button', 'Emojis').should('not.exist')
    cy.scope('dialog').contains('Update Password').should('be.visible')

    // The People page also hides its Invite affordance for non-admins.
    cy.visit('/g/people')
    cy.contains('button', 'Invite').should('not.exist')
  })
})
