// Drafts keep one name from their first keystroke: the local copy, the ?draft= link and the
// GP Draft row all use it. Each test pins one rule that follows from that, and fails if the
// rule is removed.
import { resetData } from '../../support/seed'

const CREATE = '**/api/v2/document/GP%20Draft'
const MY_DRAFTS = '/api/v2/method/gameplan.gameplan.doctype.gp_draft.gp_draft.get_my_drafts'

describe('Drafts, one name each', () => {
  let community: string
  let space: string
  let discussion: string
  let slug: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
      slug = String(ids.discussion_slug)
    })
    cy.loginAs('member')
  })

  const composer = () => cy.get('.ProseMirror').last()
  const title = () => cy.get('textarea[placeholder="Title"]')
  const draftInUrl = () =>
    cy.location('search').then((search) => new URLSearchParams(search).get('draft') ?? '')

  /** From the Drafts page: starts a discussion, types into it, yields its name, and goes back. */
  const startDiscussion = (text: string) => {
    cy.button('New discussion').click()
    cy.get('input[placeholder="Select a space"]').click()
    cy.get('[role="option"]').first().click()
    cy.button('Continue').click()
    title().type(text)
    composer().click().type(`${text} body`)
    cy.location('search').should('match', /draft=[a-z0-9]{20}/)
    return draftInUrl().then((name) => {
      cy.go('back')
      return cy.wrap(name)
    })
  }

  const visitDrafts = () => {
    cy.visit('/g/drafts')
    cy.contains('No drafts').should('be.visible')
  }

  /** Opens the composer once online: offline, its code could not load. */
  const loadComposer = () => {
    cy.button('New discussion').click()
    cy.get('input[placeholder="Select a space"]').click()
    cy.get('[role="option"]').first().click()
    cy.button('Continue').click()
    composer().should('be.visible')
    cy.go('back')
    cy.contains('No drafts').should('be.visible')
  }

  const myDrafts = () =>
    cy.request(MY_DRAFTS).its('body.data') as Cypress.Chainable<{ name: string }[]>

  it('saves a discussion started offline under the name it had from the start', () => {
    cy.intercept('POST', CREATE).as('create')
    visitDrafts()
    loadComposer()
    cy.goOffline()
    startDiscussion('Started offline').then((name) => {
      cy.contains('a', 'Started offline').should('have.attr', 'href').and('include', name)
      cy.contains('a', 'Started offline').click()
      title().should('have.value', 'Started offline')
      cy.go('back')

      cy.goOnline()
      cy.wait('@create').its('request.body.name').should('eq', name)
      myDrafts().then((drafts) => expect(drafts.map((draft) => draft.name)).to.include(name))
    })
  })

  it('keeps a draft deleted while its upload is in flight', () => {
    visitDrafts()
    loadComposer()
    cy.goOffline()
    startDiscussion('Deleted mid-upload')
    cy.button('Select').click()
    cy.contains('a', 'Deleted mid-upload').find('[data-slot="list-row-checkbox"]').click()

    // Hold the upload's create, so the delete is asked for while it is in flight.
    let uploading = false
    cy.intercept('POST', CREATE, (req) => {
      uploading = true
      req.on('response', (res) => {
        res.setDelay(3000)
      })
    })
    cy.goOnline()
    cy.wrap(null, { timeout: 10000 }).should(() => expect(uploading, 'upload in flight').to.be.true)
    cy.button('Delete 1 draft').click()
    cy.get('[role="dialog"]').contains('button', 'Delete').click()

    cy.contains('Draft deleted').should('be.visible')
    cy.reload()
    cy.contains('No drafts').should('be.visible')
    myDrafts().should('be.empty')
  })

  it('never lets an old tab bring a deleted draft back', () => {
    cy.intercept('POST', CREATE).as('create')
    cy.then(() => cy.visit(`/g/community/${community}/new-discussion?spaceId=${space}`))
    title().type('Deleted elsewhere')
    composer().click().type('first words')
    cy.wait('@create')

    // Another tab or device deletes it; this tab still holds its copy.
    draftInUrl().then((name) => {
      cy.window().then((win) =>
        win.fetch(`/api/v2/document/GP Draft/${name}`, {
          method: 'DELETE',
          headers: { 'X-Frappe-CSRF-Token': (win as unknown as { csrf_token: string }).csrf_token },
        }),
      )
      composer().click().type(' and more')

      // The server refuses the name, and this copy goes.
      cy.contains('This draft was deleted').should('be.visible')
      title().should('have.value', '')
      myDrafts().then((drafts) => expect(drafts.map((draft) => draft.name)).to.not.include(name))
    })
  })

  it('needs the connection to delete a saved draft, not an unsaved one', () => {
    cy.intercept('POST', CREATE).as('create')
    visitDrafts()
    startDiscussion('Saved first')
    cy.wait('@create')
    cy.goOffline()
    startDiscussion('Only here')

    cy.button('Select').click()
    cy.contains('a', 'Saved first').find('[data-slot="list-row-checkbox"]').click()
    cy.button('Delete 1 draft').click()
    cy.get('[role="dialog"]').contains('button', 'Delete').click()
    cy.contains("You're offline. Reconnect to do this.").should('be.visible')
    cy.contains('a', 'Saved first').should('exist')

    cy.contains('a', 'Saved first').find('[data-slot="list-row-checkbox"]').click()
    cy.contains('a', 'Only here').find('[data-slot="list-row-checkbox"]').click()
    cy.button('Delete 1 draft').click()
    cy.get('[role="dialog"]').contains('button', 'Delete').click()
    cy.contains('Draft deleted').should('be.visible')
    cy.contains('a', 'Only here').should('not.exist')
  })

  it('saves a new reply after the last one was posted as a draft of its own', () => {
    cy.intercept('POST', CREATE).as('create')
    cy.intercept('POST', '**/api/v2/document/GP%20Comment').as('postComment')
    cy.then(() =>
      cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`),
    )
    cy.button('Add a comment').click()
    composer().click().type('the first reply')
    cy.wait('@create').its('request.body.name').as('first')
    cy.button('Submit').click()
    cy.wait('@postComment')

    cy.contains('Add a comment').click()
    composer().click().type('the second reply')
    cy.wait('@create')
      .its('request.body.name')
      .then((second) => {
        cy.get('@first').should('not.eq', second)
      })
  })
})
