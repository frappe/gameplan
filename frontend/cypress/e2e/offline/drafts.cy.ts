import { resetData } from '../../support/seed'

const CREATE = '**/api/v2/document/GP%20Draft'

describe('Reply draft recovery with offline navigation', () => {
  let community: string
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
    })
    cy.loginAs('member')
  })

  const composer = () => cy.get('.ProseMirror').last()

  it('keeps saved discussion edits open when discard is refused offline', () => {
    cy.intercept('POST', CREATE).as('editDraft')
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)
    cy.selectDropdownOption('Discussion Options', 'Edit')
    cy.get('input[placeholder="Title"]').should('be.visible')
    cy.get('.ProseMirror').first().click().type('{moveToEnd} with offline discussion edits')
    cy.wait('@editDraft')
    cy.goOffline()
    cy.button('Discard').click()
    cy.contains('[role="dialog"] button', 'Discard changes').click()
    cy.contains("You're offline. Reconnect to do this.").should('be.visible')
    cy.get('input[placeholder="Title"]').should('be.visible')
    cy.get('.ProseMirror').first().should('contain.text', 'with offline discussion edits')
    cy.goOnline()
    cy.intercept('DELETE', '**/api/v2/document/GP%20Draft/*').as('discardRetry')
    cy.button('Discard').click()
    cy.contains('[role="dialog"] button', 'Discard changes').click()
    cy.wait('@discardRetry').its('response.statusCode').should('eq', 202)
    cy.get('input[placeholder="Title"]').should('not.exist')
    cy.selectDropdownOption('Discussion Options', 'Edit')
    cy.get('input[placeholder="Title"]').should('be.visible')
    cy.get('.ProseMirror').first().should('not.contain.text', 'with offline discussion edits')
  })

  it('keeps a reply typed offline when another device has one for the same discussion', () => {
    cy.intercept('POST', CREATE).as('create')
    cy.then(() => cy.visit(`/g/community/${community}/space/${space}/discussions`))
    cy.contains('a', 'Welcome thread').click()
    cy.contains('h1', 'Welcome thread').should('be.visible')

    cy.goOffline()
    cy.button('Add a comment').click()
    composer().click().type('typed offline')
    cy.go('back')
    cy.contains('a', 'Welcome thread').should('be.visible')

    // Meanwhile another device saves a reply draft of its own. cy.request is not the
    // browser's, so it gets through.
    cy.window()
      .its('csrf_token')
      .then((token) =>
        cy.request({
          method: 'POST',
          url: '/api/v2/document/GP Draft',
          headers: { 'X-Frappe-CSRF-Token': String(token) },
          body: {
            type: 'Comment',
            mode: 'New',
            reference_doctype: 'GP Discussion',
            reference_name: discussion,
            content: '<p>from the other device</p>',
          },
        }),
      )
      .its('body.data.name')
      .as('other')

    cy.goOnline()
    cy.contains('a', 'Welcome thread').click()
    cy.get('body').then(($body) => {
      if (!$body.find('.ProseMirror').length) cy.button('Add a comment').click()
    })
    composer().should('contain.text', 'typed offline')
    composer().click().type(' and more')

    // Saved as a draft of its own, not as an update to the other device's row.
    cy.wait('@create').then(({ request }) => {
      expect(request.body.content).to.include('typed offline')
      cy.get('@other').should('not.eq', request.body.name)
    })
    cy.contains('This draft was deleted').should('not.exist')
    composer().should('contain.text', 'typed offline and more')
  })
})
