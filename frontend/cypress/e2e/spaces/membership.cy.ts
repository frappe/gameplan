import { resetData } from '../../support/seed'

describe('Space membership', () => {
  let community: string
  let space: string

  beforeEach(() => {
    resetData('unread_discussion').then((ids) => {
      community = ids.community as string
      space = String(ids.space)
    })
    cy.loginAs('member')
  })

  function spaceRow(title: string) {
    return cy.contains('[data-slot="sidebar-item"] a', title).closest('[data-slot="sidebar-item"]')
  }

  it('joins, marks read, and leaves a space', () => {
    cy.intercept('POST', '**/join_spaces').as('joinSpace')
    cy.intercept('POST', '**/track_visits').as('trackSpaceVisit')
    cy.intercept('POST', '**/get_unread_count').as('loadUnreadCounts')
    cy.intercept('POST', '**/mark_all_as_read').as('markSpaceRead')
    cy.intercept('POST', '**/leave_spaces').as('leaveSpace')

    cy.visit(`/g/community/${community}/space/${space}`)
    cy.wait('@trackSpaceVisit').its('response.statusCode').should('eq', 200)
    cy.wait('@loadUnreadCounts').its('response.statusCode').should('eq', 200)
    spaceRow('General').find('[data-slot="sidebar-item-suffix"]').should('contain.text', '1')

    cy.selectDropdownOption('Space actions', 'Join space')
    cy.wait('@joinSpace').its('response.statusCode').should('eq', 200)
    cy.request('GET', '/api/v2/method/GP%20Project/get_joined_spaces')
      .its('body.data')
      .should('include', space)

    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Leave space').should('be.visible')
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Follow space')
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Unfollow space')
    cy.get('body').type('{esc}')

    // Exercise the sidebar's bulk endpoint: autonumbered Space ids can originate as
    // numbers in list responses, but the typed API contract receives strings.
    spaceRow('General').trigger('mouseover')
    spaceRow('General').find('button[aria-label="General options"]').click()
    cy.get('[role="menuitem"]:visible').contains('Mark all as read').click()
    cy.scope('dialog').button('Mark all as read').click()
    cy.wait('@markSpaceRead').then(({ request, response }) => {
      expect(request.body.spaces).to.deep.equal([space])
      expect(response?.statusCode).to.equal(200)
    })
    spaceRow('General').find('[data-slot="sidebar-item-suffix"]').should('not.contain.text', '1')

    // Leaving always confirms first. On a public space the warning is mild, because
    // rejoining is one click away from the same menu.
    cy.selectDropdownOption('Space actions', 'Leave space')
    cy.scope('dialog').should('contain.text', 'Leave "General"?')
    cy.scope('dialog').should('contain.text', 'You can rejoin at any time.')
    cy.scope('dialog').button('Leave').click()
    cy.wait('@leaveSpace').its('response.statusCode').should('eq', 200)

    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Join space').should('be.visible')

    cy.request('GET', '/api/v2/method/GP%20Project/get_joined_spaces')
      .its('body.data')
      .should('not.include', space)
  })

  it('keeps archived spaces read-only in the actions menu', () => {
    cy.loginAs('admin')
    cy.request('POST', `/api/v2/document/GP%20Project/${space}/method/archive`)
    cy.loginAs('member')

    cy.visit(`/g/community/${community}/space/${space}`)
    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Copy link').should('be.visible')
    cy.get('[role="menuitem"]:visible').contains('Mark all as read').should('be.visible')
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Join space')
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Leave space')
  })
})

describe('Private space membership', () => {
  let community: string
  let privateSpace: string

  beforeEach(() => {
    // "Secret Plans" is private with member as its only member. The guest reaches it
    // through a GP Guest Access row instead of a membership, which is what makes the
    // membership control meaningless for them.
    resetData('private_space_with_guest').then((ids) => {
      community = String(ids.community)
      privateSpace = String(ids.private_space)
    })
  })

  it('warns a member that leaving a private space is one-way', () => {
    cy.loginAs('member')
    cy.intercept('POST', '**/leave_spaces').as('leaveSpace')

    cy.visit(`/g/community/${community}/space/${privateSpace}`)
    cy.contains('a', 'Secret thread').should('be.visible')

    // Cancelling must not leave. On a private space `can_view_space` is exactly
    // membership, so an accidental click would cost the member their access to the
    // space — and with it the Join action that would undo it.
    cy.selectDropdownOption('Space actions', 'Leave space')
    cy.scope('dialog').should('contain.text', 'Leave "Secret Plans"?')
    cy.scope('dialog').should(
      'contain.text',
      "This space is private. You won't be able to rejoin unless a member adds you back.",
    )
    cy.scope('dialog').button('Cancel').click()
    cy.get('[role="dialog"]').should('not.exist')
    cy.request('GET', '/api/v2/method/GP%20Project/get_joined_spaces')
      .its('body.data')
      .should('include', privateSpace)

    cy.selectDropdownOption('Space actions', 'Leave space')
    cy.scope('dialog').button('Leave').click()
    cy.wait('@leaveSpace').its('response.statusCode').should('eq', 200)
    cy.request('GET', '/api/v2/method/GP%20Project/get_joined_spaces')
      .its('body.data')
      .should('not.include', privateSpace)
  })

  it('hides the membership control from a guest', () => {
    cy.loginAs('guest')

    cy.visit(`/g/community/${community}/space/${privateSpace}`)
    cy.contains('a', 'Secret thread').should('be.visible')

    // `get_joined_spaces` unions guest grants with memberships, so the granted space
    // looks joined to a guest while `leave_spaces` only ever touches member rows —
    // the control could only render as a button that does nothing. The menu itself
    // still opens (Copy link proves it rendered), it just carries no membership item.
    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Copy link').should('be.visible')
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Leave space')
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Join space')

    // Same class of dead control: the backend refuses a bulk move from a guest, so
    // offering the mode only leads to a rejected request.
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Move discussions')
  })
})
