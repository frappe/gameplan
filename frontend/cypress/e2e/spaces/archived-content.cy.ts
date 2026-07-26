import { resetData } from '../../support/seed'

describe('Archived space content', () => {
  let community: string
  let space: string
  let page: string
  let task: string

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)

      cy.request('POST', '/api/v2/document/GP%20Page', {
        title: 'Archived handbook',
        content: '<p>Existing guidance stays available.</p>',
        project: space,
      }).then(({ body }) => {
        page = String(body.data.name)
      })
      cy.request('POST', '/api/v2/document/GP%20Task', {
        title: 'Archived follow-up',
        description: '<p>Existing work stays available.</p>',
        project: space,
      }).then(({ body }) => {
        task = String(body.data.name)
      })
      cy.request('POST', `/api/v2/document/GP%20Project/${space}/method/archive`)
    })
    cy.loginAs('member')
  })

  it('keeps pages and tasks viewable without creation or editing controls', () => {
    cy.visit(`/g/community/${community}/space/${space}/pages`)
    cy.contains('a', 'Archived handbook').should('be.visible')
    cy.button('Add new').should('not.exist')
    cy.contains('a', 'Archived handbook').click()
    cy.url().should('include', `/space/${space}/pages/${page}`)
    cy.get('input[placeholder="Title"]')
      .should('have.value', 'Archived handbook')
      .and('have.attr', 'readonly')
    cy.get('[contenteditable=false]').should('contain.text', 'Existing guidance stays available.')
    cy.iconButton('Page Options').should('not.exist')

    cy.visit(`/g/community/${community}/space/${space}/tasks`)
    cy.contains('a', 'Archived follow-up').should('be.visible')
    cy.button('Add new').should('not.exist')
    cy.contains('a', 'Archived follow-up').click()
    cy.url().should('include', `/tasks/${task}`)

    let updateRequests = 0
    cy.intercept('PUT', `/api/v2/document/GP%20Task/${task}`, () => {
      updateRequests += 1
    })

    cy.get('input[placeholder="Title"]')
      .should('have.value', 'Archived follow-up')
      .and('have.attr', 'readonly')
    cy.get('input[placeholder="Title"]').focus().blur()
    cy.get('[contenteditable=false]').should('contain.text', 'Existing work stays available.')
    cy.contains('div', /^Assignee$/).next('div').find('button').should('be.disabled')
    cy.get('input[placeholder="Due date"]:visible').should('be.disabled')
    cy.contains('div', /^Space$/).next('div').find('button').should('be.disabled')
    cy.contains('div', /^Status$/).next('div').find('[role="combobox"]').should('be.disabled')
    cy.contains('div', /^Priority$/).next('div').find('[role="combobox"]').should('be.disabled')
    cy.get('input[placeholder="Title"]').parent().find('button[aria-haspopup="menu"]').should('not.exist')
    cy.contains('Cannot modify tasks.').should('not.exist')
    cy.then(() => expect(updateRequests, 'task update requests').to.equal(0))
  })
})
