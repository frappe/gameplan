// A bookmark is a private reading list: save a post or a comment from its menu, find it
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
    cy.contains('a', 'Welcome thread').should('be.visible').and('contain', 'Seed content').click()
    cy.url().should('include', `/discussion/${discussion}`)

    cy.selectDropdownOption('Discussion Options', 'Remove Bookmark')
    cy.wait('@removeBookmark')

    cy.visit('/g/bookmarks')
    cy.contains('div', 'No discussions').should('be.visible')
    cy.contains('a', 'Welcome thread').should('not.exist')
  })

  it('bookmarks a comment, opens it from Bookmarks, and removes it', () => {
    cy.request({
      method: 'POST',
      url: '/api/v2/document/GP%20Comment',
      body: {
        reference_doctype: 'GP Discussion',
        reference_name: discussion,
        content: '<p>Ship it on Friday</p>',
      },
    }).then((response) => {
      const comment = String(response.body.data.name)

      cy.intercept('POST', `/api/v2/document/GP%20Comment/${comment}/method/add_bookmark`).as(
        'addBookmark',
      )
      cy.intercept('POST', `/api/v2/document/GP%20Comment/${comment}/method/remove_bookmark`).as(
        'removeBookmark',
      )

      visitDiscussion()
      cy.get(`div[data-id="${comment}"]`).should('contain', 'Ship it on Friday')

      cy.selectDropdownOption('Comment Options', 'Bookmark')
      cy.wait('@addBookmark')

      cy.get('button[aria-haspopup=menu][aria-label="Comment Options"]').click()
      cy.get('[role="menuitem"]:contains("Remove Bookmark"):visible').should('exist')
      cy.get('body').type('{esc}')

      openDiscussionOptions()
      cy.get('[role="menuitem"]:contains("Remove Bookmark"):visible').should('not.exist')
      cy.get('body').type('{esc}')

      cy.visit('/g/bookmarks')
      cy.contains('a', 'Welcome thread')
        .should('be.visible')
        .and('contain', 'Ship it on Friday')
        .click()
      cy.url().should('include', `/discussion/${discussion}`).and('include', `comment=${comment}`)
      cy.get(`div[data-id="${comment}"]`).should('be.visible')

      cy.selectDropdownOption('Comment Options', 'Remove Bookmark')
      cy.wait('@removeBookmark')

      cy.visit('/g/bookmarks')
      cy.contains('div', 'No discussions').should('be.visible')
    })
  })
})
