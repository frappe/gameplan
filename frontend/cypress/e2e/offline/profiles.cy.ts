// People and profiles offline: one opened online reads again without a connection, and one
// that was never opened says so rather than rendering as an empty profile.
import { resetData } from '../../support/seed'
import { personas } from '../../support/personas'

describe('People offline', () => {
  beforeEach(() => {
    resetData('space_with_discussion')
    cy.loginAs('member')
  })

  it('reads a profile that was opened online', () => {
    cy.visit('/g/people')
    cy.contains(personas.secondMember.displayName, { timeout: 20000 }).should('be.visible').click()
    cy.url().should('include', '/people/')
    cy.button('Profile').should('be.visible')

    cy.visit('/g/people')
    cy.contains(personas.secondMember.displayName).should('be.visible')

    cy.goOffline()
    cy.contains(personas.secondMember.displayName).click()
    cy.url().should('include', '/people/')
    cy.button('Profile').should('be.visible')
    cy.contains(personas.secondMember.displayName).should('be.visible')
    cy.contains(/can't load .* while offline/i).should('not.exist')

    cy.goOnline()
  })

  it('says so for a profile this browser never opened', () => {
    // The People list is cached by visiting it; the individual profile is not.
    cy.visit('/g/people')
    cy.contains(personas.outsider.displayName, { timeout: 20000 }).should('be.visible')

    cy.goOffline()
    cy.contains(personas.outsider.displayName).click()
    cy.contains(/can't load .* while offline/i, { timeout: 20000 }).should('be.visible')
    cy.button('Retry').should('be.visible')

    cy.goOnline()
  })

  it('refreshes cached cards on reconnect and on a later visit', () => {
    let version = 0
    cy.intercept('GET', '**/api/v2/method/*get_bento_cards*', (req) =>
      req.reply({
        body: {
          data: {
            profile: req.query.profile,
            is_default: false,
            cards: [
              {
                id: 'notes',
                type: 'Card',
                size: '2x1',
                source: 'custom',
                title: 'Notes',
                text: `Cards version ${++version}`,
              },
            ],
          },
        },
      }),
    ).as('cards')
    cy.visit('/g/people')
    cy.contains(personas.secondMember.displayName).click()
    cy.button('Profile').click()
    cy.contains('Cards version 1').should('be.visible')
    cy.goOffline()
    cy.goOnline()
    cy.contains('Cards version 2', { timeout: 10000 }).should('be.visible')
    cy.get('a[href="/g/people"]').filter(':visible').first().click()
    cy.contains(personas.secondMember.displayName).click()
    cy.button('Profile').click()
    cy.contains('Cards version 3').should('be.visible')
  })
})
