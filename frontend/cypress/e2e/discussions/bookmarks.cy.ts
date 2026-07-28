// A bookmark is a private reading list: save a discussion from its own page, find it
// again under Bookmarks, and take it back off the list.
import { resetData } from '../../support/seed'

describe('Bookmarks', () => {
  let community: string
  let space: string
  let discussion: string
  let discussionSlug: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
      discussionSlug = String(ids.discussion_slug)
    })
    cy.loginAs('member')
  })

  const visitDiscussion = () =>
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${discussionSlug}`)

  const openDiscussionOptions = () =>
    cy.get('button[aria-haspopup=menu][aria-label="Discussion Options"]').click()

  it('bookmarks a discussion, finds it under Bookmarks, and removes it', () => {
    cy.intercept('POST', `/api/v2/document/GP%20Discussion/${discussion}/method/add_bookmark`).as(
      'addBookmark',
    )
    cy.intercept(
      'POST',
      `/api/v2/document/GP%20Discussion/${discussion}/method/remove_bookmark`,
    ).as('removeBookmark')

    visitDiscussion()
    cy.contains('h1', 'Welcome thread').should('be.visible')

    cy.selectDropdownOption('Discussion Options', 'Bookmark')
    cy.wait('@addBookmark')

    // The same menu now offers to take the bookmark back — without a reload.
    openDiscussionOptions()
    cy.get('[role="menuitem"]:contains("Remove Bookmark"):visible').should('exist')
    cy.get('[role="menuitem"]:contains("Bookmark"):visible').should('have.length', 1)
    cy.get('body').type('{esc}')

    cy.visit('/g/bookmarks')
    cy.contains('a', 'Welcome thread').should('be.visible').click()
    cy.url().should('include', `/discussion/${discussion}`)

    cy.selectDropdownOption('Discussion Options', 'Remove Bookmark')
    cy.wait('@removeBookmark')

    cy.visit('/g/bookmarks')
    cy.contains('div', 'No discussions').should('be.visible')
    cy.contains('a', 'Welcome thread').should('not.exist')
  })
})
