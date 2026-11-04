import { resetData } from '../../support/seed'

describe('Edits interrupted by a lost connection', () => {
  let community: string
  let space: string

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
    })
    cy.loginAs('member')
  })

  it('reports a page edit whose autosave runs after disconnecting', () => {
    cy.request('POST', '/api/v2/document/GP%20Page', {
      title: 'Page before disconnect',
      content: '<p>Original content</p>',
      project: space,
    }).then(({ body }) => {
      cy.visit(`/g/community/${community}/space/${space}/pages/${body.data.name}`)
      cy.get('input[placeholder="Title"]').should('have.value', 'Page before disconnect')
      cy.clock(Date.now(), ['setTimeout', 'clearTimeout'])
      cy.get('input[placeholder="Title"]').type(' with unsaved changes')
      cy.goOffline()
      cy.tick(1000)
      cy.contains('Could not save the page').should('be.visible')
      cy.get('input[placeholder="Title"]').should(
        'have.value',
        'Page before disconnect with unsaved changes',
      )
    })
  })

  for (const [field, edited] of [
    ['title', true],
    ['description', true],
    ['title', false],
    ['description', false],
  ] as const) {
    it(`${edited ? 'reports an unsaved' : 'stays quiet for an unchanged'} task ${field} after disconnecting`, () => {
      cy.request('POST', '/api/v2/document/GP%20Task', {
        title: 'Task before disconnect',
        description: '<p>Original description</p>',
        project: space,
      }).then(({ body }) => {
        cy.visit(`/g/community/${community}/space/${space}/tasks/${body.data.name}`)
        cy.get('input[placeholder="Title"]').should('have.value', 'Task before disconnect')
        const editor = () =>
          field === 'title' ? cy.get('input[placeholder="Title"]') : cy.get('.ProseMirror').first()
        editor().click()
        if (edited) editor().type(`{selectall}Unsaved task ${field}`)
        cy.goOffline()
        if (field === 'title') editor().blur()
        else cy.get('input[placeholder="Title"]').focus()
        if (edited) cy.contains('Could not save the task').should('be.visible')
        else {
          cy.wait(1500)
          cy.contains('Could not save the task').should('not.exist')
        }
      })
    })
  }

  for (const saved of [false, true]) {
    it(`${saved ? 'keeps a saved' : 'deletes a local-only'} draft from its composer offline`, () => {
      cy.intercept('POST', '**/api/v2/document/GP%20Draft').as('createDraft')
      cy.then(() => cy.visit(`/g/community/${community}/new-discussion?spaceId=${space}`))
      cy.get('textarea[placeholder="Title"]').should('not.be.disabled')
      if (!saved) cy.goOffline()
      cy.get('textarea[placeholder="Title"]').type('Draft to delete offline')
      cy.location('search').should('include', 'draft=')
      if (saved) {
        cy.wait('@createDraft')
        cy.goOffline()
      }
      cy.get('button[aria-label="More publish options"]:visible').click()
      cy.contains('[role="menuitem"]', 'Delete draft').click()
      cy.contains('[role="dialog"] button', 'Delete draft').click()
      if (saved) {
        cy.contains("You're offline. Reconnect to do this.").should('be.visible')
        cy.get('textarea[placeholder="Title"]').should('have.value', 'Draft to delete offline')
      } else {
        cy.location('pathname').should('eq', '/g/drafts')
        cy.contains('No drafts').should('be.visible')
      }
      cy.goOnline()
    })
  }
})
