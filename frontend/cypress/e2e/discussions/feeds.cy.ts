// The community discussions page: its three feeds, the community actions menu, and
// marking a whole community as read.
import { resetData } from '../../support/seed'

describe('Community discussion feeds', () => {
  let community: string
  // "General": holds the seeded discussion, written by member2 so it is unread for member.
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('unread_discussion').then((ids) => {
      community = ids.community as string
      space = ids.space as string
      discussion = ids.discussion as string
    })
    cy.loginAs('member')
  })

  it('switches between the all, participating and unread feeds', () => {
    cy.visit(`/g/community/${community}/discussions`)

    cy.contains('button:visible', 'All Discussions').should('be.visible')
    cy.contains('button:visible', 'Participating').should('be.visible')
    cy.contains('button:visible', 'Unread').should('be.visible')
    cy.contains('Unread thread').should('be.visible')

    cy.contains('button:visible', 'Participating').first().click()
    cy.url().should('include', `/community/${community}/discussions/participating`)

    cy.contains('button:visible', 'Unread').first().click()
    cy.url().should('include', `/community/${community}/discussions/unread`)
    cy.contains('Unread thread').should('be.visible')
  })

  // Managing a community is an admin-only power: "Manage spaces" and "Manage users"
  // only render for a community admin or a global admin, so this one acts as admin.
  it('opens community management from the community actions menu', () => {
    cy.loginAs('admin')
    cy.visit(`/g/community/${community}/discussions`)

    cy.scope('header')
      .contains('a', 'Acme')
      .parent()
      .within(() => {
        cy.iconButton('Community actions').should('be.visible')
      })

    // Community management lives in the Settings dialog: both actions open the
    // Communities tab at /g/settings/communities (the target community + view are
    // held in memory, not the URL).
    cy.iconButton('Community actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Manage spaces').first().click()
    cy.url().should('include', '/g/settings/communities')

    cy.visit(`/g/community/${community}/discussions`)
    cy.iconButton('Community actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Manage users').first().click()
    cy.url().should('include', '/g/settings/communities')
  })

  it('marks every discussion in the community as read', () => {
    cy.visit(`/g/community/${community}/discussions/unread`)
    cy.contains('Unread thread').should('be.visible')

    cy.iconButton('Community actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Mark all as read').first().click()
    cy.scope('dialog').button('Mark all as read').first().click()

    cy.contains('Unread thread').should('not.exist')
    cy.contains('No discussions').should('be.visible')

    // Only System Manager can read GP Unread Record, so verify the row as admin.
    cy.loginAs('admin')
    cy.request('POST', '/api/method/frappe.client.get_value', {
      doctype: 'GP Unread Record',
      filters: {
        user: 'member@example.com',
        discussion,
        project: space,
      },
      fieldname: 'is_unread',
    })
      .its('body.message.is_unread')
      .should('eq', 0)
  })
})
