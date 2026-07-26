// Everything a member can do to a discussion: publish one into a space, comment
// on it, rename it, edit its content, move it to another space, and close it.
import { resetData } from '../../support/seed'

describe('Discussion actions', () => {
  let community: string
  // "Engineering": holds the seeded discussion "Welcome thread".
  let space: string
  // The empty auto-created "General": the publish target and the move target.
  let generalSpace: string
  let discussion: string
  let discussionSlug: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = ids.community as string
      space = ids.space as string
      generalSpace = ids.general_space as string
      discussion = ids.discussion as string
      discussionSlug = ids.discussion_slug as string
    })
    cy.loginAs('member')
  })

  function visitSeededDiscussion() {
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${discussionSlug}`)
  }

  it('publishes a new discussion into a space', () => {
    // Publishing flushes the draft and calls the whitelisted `publish_draft` method,
    // which returns the new discussion name as the response `message`.
    cy.intercept({
      method: 'POST',
      url: '/api/method/gameplan.gameplan.doctype.gp_draft.gp_draft.publish_draft',
      times: 1,
    }).as('publishDraft')

    cy.visit(`/g/community/${community}/space/${generalSpace}/discussions`)
    cy.contains('div', 'No discussions')

    // "Add new" from a space carries that space in the route, so the composer
    // needs no space picked.
    cy.button('Add new').click()
    // Type into the editor first so TipTap finishes initializing; otherwise it
    // steals focus while the title is being typed and drops the title's first
    // keystroke, which corrupts the published slug.
    cy.get('div[contenteditable=true]')
      .should('be.visible')
      .click()
      .type('This is content for new discussion{enter}')
    cy.get('textarea')
      .should('be.visible')
      .click()
      .type('Starting a new discussion')
      .should('have.value', 'Starting a new discussion')
    cy.button('Publish').click()

    cy.wait('@publishDraft')
      .its('response.body.message')
      .then((discussionId: string) => {
        cy.url().should('include', `/discussion/${discussionId}/starting-a-new-discussion`)
      })
  })

  it('adds a comment to a discussion', () => {
    cy.intercept('POST', '/api/v2/document/GP%20Comment').as('comment')
    visitSeededDiscussion()

    cy.button('Add a comment').click()
    // Click the editor to settle focus and expand the composer before typing —
    // relying on cy.focused() races the just-mounted ProseMirror view (drops the
    // first keystroke) and can leave the composer collapsed so Submit never shows.
    cy.get('[contenteditable=true]').should('be.visible').click().type('This is the first comment')
    cy.button('Submit').click()

    cy.wait('@comment')
      .its('response.body.data')
      .then((comment: { name: string }) => {
        cy.get(`div[data-id="${comment.name}"]`).should('exist')
      })
  })

  it('renames a discussion and records the rename in the activity feed', () => {
    visitSeededDiscussion()

    cy.selectDropdownOption('Discussion Options', 'Edit')
    cy.get('input[placeholder="Title"]')
      .should('be.visible')
      .type(' {selectall}', { delay: 200 })
      .type('Edited Discussion Title')
    cy.button('Save').click()

    cy.contains('h1', 'Edited Discussion Title').should('be.visible')
    cy.contains('changed the title from').should('exist')
  })

  it('edits the content of a discussion', () => {
    visitSeededDiscussion()

    cy.selectDropdownOption('Discussion Options', 'Edit')
    cy.get('[contenteditable=true]')
      .should('be.visible')
      .click()
      .type('{moveToEnd} adding more content')
    cy.button('Save').click()

    cy.contains('p', 'adding more content').should('exist')
  })

  it('blocks post editing until its draft finishes loading', () => {
    cy.intercept(/find_my_draft/, (request) => {
      request.continue((response) => response.setDelay(1500))
    }).as('editDraft')
    visitSeededDiscussion()

    cy.selectDropdownOption('Discussion Options', 'Edit')
    cy.contains('[role="status"]', 'Loading draft…').should('be.visible')
    cy.get('input[placeholder="Title"]').should('be.disabled')
    cy.get('[contenteditable]').should('have.attr', 'contenteditable', 'false')

    cy.wait('@editDraft')
    cy.contains('[role="status"]', 'Loading draft…').should('not.exist')
    cy.get('input[placeholder="Title"]').should('be.enabled').type(' after load')
    cy.get('[contenteditable]')
      .should('have.attr', 'contenteditable', 'true')
      .click()
      .type('{moveToEnd} after load')
    cy.get('input[placeholder="Title"]').should('have.value', 'Welcome thread after load')
    cy.get('[contenteditable]').should('contain.text', 'after load')
  })

  it('moves a discussion to another space', () => {
    visitSeededDiscussion()

    cy.selectDropdownOption('Discussion Options', 'Move to...')
    // "General" is the only other space in the seeded community.
    cy.selectCombobox('Select a project', 'General')
    cy.button('Move to General').click()

    cy.url().should(
      'include',
      `/g/community/${community}/space/${generalSpace}/discussion/${discussion}`,
    )
  })

  it('closes a discussion so nobody can comment on it', () => {
    visitSeededDiscussion()

    cy.selectDropdownOption('Discussion Options', 'Close discussion')
    cy.dialog('button').contains('Close').click()

    cy.contains('closed this discussion').should('exist')
    cy.button('Add a comment').should('not.exist')
  })
})
