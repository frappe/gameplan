import { resetData } from '../../support/seed'

describe('Space actions', () => {
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

  it('marks a space read from the sidebar', () => {
    cy.intercept('POST', '**/track_visits').as('trackSpaceVisit')
    cy.intercept('POST', '**/get_unread_count').as('loadUnreadCounts')
    cy.intercept('POST', '**/mark_all_as_read').as('markSpaceRead')

    cy.visit(`/g/community/${community}/space/${space}`)
    cy.wait('@trackSpaceVisit').its('response.statusCode').should('eq', 200)
    cy.wait('@loadUnreadCounts').its('response.statusCode').should('eq', 200)
    spaceRow('General').find('[data-slot="sidebar-item-suffix"]').should('contain.text', '1')

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
  })

  it('keeps archived spaces read-only in the actions menu', () => {
    cy.loginAs('admin')
    cy.request('POST', `/api/v2/document/GP%20Project/${space}/method/archive`)
    cy.loginAs('member')

    cy.visit(`/g/community/${community}/space/${space}`)
    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Copy link').should('be.visible')
    cy.get('[role="menuitem"]:visible').contains('Mark all as read').should('be.visible')
  })
})

describe('Private space actions', () => {
  let community: string
  let privateSpace: string

  beforeEach(() => {
    // "Secret Plans" is private with member as its only member. The guest reaches it
    // through a GP Guest Access row instead of a membership.
    resetData('private_space_with_guest').then((ids) => {
      community = String(ids.community)
      privateSpace = String(ids.private_space)
    })
  })

  it('offers a guest no bulk move', () => {
    cy.loginAs('guest')

    cy.visit(`/g/community/${community}/space/${privateSpace}`)
    cy.contains('a', 'Secret thread').should('be.visible')

    // The menu opens (Copy link proves it rendered), but without Move discussions:
    // the backend refuses a bulk move from a guest, so offering the mode only leads
    // to a rejected request.
    cy.iconButton('Space actions').first().click()
    cy.get('[role="menuitem"]:visible').contains('Copy link').should('be.visible')
    cy.get('[role="menuitem"]:visible').should('not.contain.text', 'Move discussions')
  })
})
