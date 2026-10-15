import { resetData } from '../../support/seed'

describe('Failed requests keep the right UI state', () => {
  let community: string
  let space: string
  let general: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      general = String(ids.general_space)
    })
    cy.loginAs('member')
  })

  it('keeps newer pins when an earlier save fails before the next debounce', () => {
    let failFirst: (() => void) | undefined
    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*', (req) => {
      if (failFirst) return
      return new Cypress.Promise<void>((resolve) => {
        failFirst = () => {
          req.reply({ statusCode: 500, body: {} })
          resolve()
        }
      })
    }).as('savePins')
    cy.then(() => cy.visit(`/g/community/${community}/discussions`))
    cy.contains('a', 'Welcome thread').should('be.visible')
    cy.clock(Date.now(), ['setTimeout', 'clearTimeout'])

    cy.get('button[aria-label="General options"]').click({ force: true })
    cy.contains('[role="menuitem"]', 'Pin space').click()
    cy.tick(500)
    cy.wrap(null).should(() => expect(failFirst, 'first save is held').to.be.a('function'))

    cy.get('button[aria-label="Engineering options"]').click({ force: true })
    cy.contains('[role="menuitem"]', 'Pin space').click()
    cy.then(() => failFirst?.())
    cy.wait('@savePins').its('response.statusCode').should('eq', 500)
    cy.get('button[aria-label="Engineering options"]').click({ force: true })
    cy.contains('[role="menuitem"]', 'Unpin space').should('be.visible')
    cy.get('body').type('{esc}')

    cy.tick(500)
    cy.wait('@savePins').then(({ request, response }) => {
      expect(JSON.parse(request.body.pinned_spaces)).to.have.members([general, space])
      expect(response?.statusCode).to.eq(200)
    })
  })

  it('shows a failed People request instead of an empty list', () => {
    cy.intercept('GET', '**/api/v2/method/*gp_user_profile.get_list*', {
      statusCode: 500,
      body: { errors: [{ message: 'People request failed', type: 'ValidationError' }] },
    }).as('people')
    cy.visit('/g/people')
    cy.wait('@people')
    cy.contains('[role="alert"]', 'People request failed').should('be.visible')
    cy.contains('No members yet').should('not.exist')
  })

  it('rolls back a failed pin save when there is no newer toggle', () => {
    cy.intercept('PUT', '**/api/v2/document/GP%20User%20Profile/*', {
      statusCode: 500,
      body: {},
    }).as('savePins')
    cy.then(() => cy.visit(`/g/community/${community}/discussions`))
    cy.contains('a', 'Welcome thread').should('be.visible')
    cy.get('button[aria-label="General options"]').click({ force: true })
    cy.contains('[role="menuitem"]', 'Pin space').click()
    cy.wait('@savePins')
    cy.get('button[aria-label="General options"]').click({ force: true })
    cy.contains('[role="menuitem"]', 'Pin space').should('be.visible')
  })
})
