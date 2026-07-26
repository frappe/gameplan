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
    cy.get('[role="menuitem"]:visible').contains('Mark all as read').click()
    cy.scope('dialog').button('Mark all as read').click()
    cy.wait('@markSpaceRead').its('response.statusCode').should('eq', 200)
    spaceRow('General').find('[data-slot="sidebar-item-suffix"]').should('not.contain.text', '1')

    cy.selectDropdownOption('Space actions', 'Leave space')
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
