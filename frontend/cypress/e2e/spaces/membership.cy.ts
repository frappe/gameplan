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

  function getList(
    doctype: string,
    filters: Record<string, string>,
    fields: string[] = ['name'],
  ) {
    return cy
      .request({
        method: 'GET',
        url: '/api/method/frappe.client.get_list',
        qs: {
          doctype,
          filters: JSON.stringify(filters),
          fields: JSON.stringify(fields),
        },
      })
      .its('body.message')
  }

  it('joins, follows, marks read, unfollows, and leaves a space', () => {
    cy.intercept('POST', '**/join_spaces').as('joinSpace')
    cy.intercept('POST', '**/track_visits').as('trackSpaceVisit')
    cy.intercept('POST', '**/follow_spaces').as('followSpace')
    cy.intercept('POST', '**/mark_all_as_read').as('markSpaceRead')
    cy.intercept('POST', '**/unfollow_spaces').as('unfollowSpace')
    cy.intercept('POST', '**/leave_spaces').as('leaveSpace')

    cy.visit(`/g/community/${community}/space/${space}`)
    cy.wait('@trackSpaceVisit').its('response.statusCode').should('eq', 200)

    getList(
      'GP Project Visit',
      { project: space, user: 'member@example.com' },
      ['name', 'last_visit', 'mark_all_read_at'],
    ).then((visits) => {
      expect(visits).to.have.length(1)
      expect(visits[0].last_visit).to.be.a('string').and.not.be.empty
      expect(visits[0].mark_all_read_at).to.be.null
    })

    cy.selectDropdownOption('Space actions', 'Join space')
    cy.wait('@joinSpace').its('response.statusCode').should('eq', 200)

    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Leave space').should('be.visible')
    cy.get('[role="menuitem"]:visible').contains('Follow space').click()
    cy.wait('@followSpace').its('response.statusCode').should('eq', 200)

    getList(
      'GP Followed Project',
      { project: space, user: 'member@example.com' },
      ['name', 'project', 'user'],
    ).should('have.length', 1)

    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Unfollow space').should('be.visible')
    cy.get('[role="menuitem"]:visible').contains('Mark all as read').click()
    cy.scope('dialog').button('Mark all as read').click()
    cy.wait('@markSpaceRead').its('response.statusCode').should('eq', 200)

    getList(
      'GP Project Visit',
      { project: space, user: 'member@example.com' },
      ['name', 'last_visit', 'mark_all_read_at'],
    ).then((visits) => {
      expect(visits).to.have.length(1)
      expect(visits[0].last_visit).to.be.a('string').and.not.be.empty
      expect(visits[0].mark_all_read_at).to.be.a('string').and.not.be.empty
    })

    cy.selectDropdownOption('Space actions', 'Unfollow space')
    cy.wait('@unfollowSpace').its('response.statusCode').should('eq', 200)
    getList('GP Followed Project', {
      project: space,
      user: 'member@example.com',
    }).should('have.length', 0)

    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Follow space').should('be.visible')
    cy.get('[role="menuitem"]:visible').contains('Leave space').click()
    cy.wait('@leaveSpace').its('response.statusCode').should('eq', 200)

    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Join space').should('be.visible')

    cy.request('GET', '/api/v2/method/GP%20Project/get_joined_spaces')
      .its('body.data')
      .should('not.include', space)
  })
})
