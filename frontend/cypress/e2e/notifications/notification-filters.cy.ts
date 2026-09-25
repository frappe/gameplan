import { resetData } from '../../support/seed'

describe('Notification filters', () => {
  let alpha: string
  let beta: string
  let alphaSpace: string
  let betaSpace: string

  const mentionHtml =
    '<p>Ping <span data-type="mention" data-id="member@example.com" data-label="Member">@Member</span></p>'

  beforeEach(() => {
    resetData('two_communities').then((ids) => {
      ;[alpha, beta] = (ids.communities as string[]).map(String)
      ;[alphaSpace, betaSpace] = (ids.spaces as string[]).map(String)
    })
    cy.then(() => {
      // The filter row earns its place only from five rows up (FILTERS_FROM in
      // Notifications.vue), so the two threads the assertions name are padded out to it.
      // The padding sits in Alpha's space, where nothing asserts on row counts.
      for (const [space, title] of [
        [alphaSpace, 'Alpha thread'],
        [betaSpace, 'Beta thread'],
        [alphaSpace, 'Padding one'],
        [alphaSpace, 'Padding two'],
        [alphaSpace, 'Padding three'],
      ]) {
        cy.task('requestAsUser', {
          user: 'member2@example.com',
          method: 'POST',
          path: '/api/v2/document/GP Discussion',
          body: { title, project: space, content: mentionHtml },
        })
      }
    })
    cy.loginAs('member')
    cy.intercept('GET', '**/api/v2/document/GP%20Notification*').as('notificationList')
    cy.visit('/g/notifications')
    cy.wait('@notificationList')
  })

  it('lists both mentions under a day label', () => {
    cy.contains('[data-slot="list-group-header"]', 'Today').should('be.visible')
    cy.contains('Alpha thread').should('be.visible')
    cy.contains('Beta thread').should('be.visible')
  })

  it('narrows to the picked community', () => {
    cy.button('All communities').click()
    cy.contains('[role="option"]', 'Alpha').click()
    cy.get('body').type('{esc}')
    cy.wait('@notificationList')

    cy.contains('Alpha thread').should('be.visible')
    cy.contains('Beta thread').should('not.exist')
    cy.button('Alpha').should('be.visible').click()
    cy.contains('[role="option"]', 'Beta').click()
    cy.get('body').type('{esc}')
    cy.button('2 communities').should('be.visible')

    cy.button('Clear').click()
    cy.wait('@notificationList')
    cy.contains('Beta thread').should('be.visible')
  })

  it('narrows to the picked space', () => {
    cy.button('All spaces').click()
    cy.contains('[role="option"]', 'Beta Space').click()
    cy.get('body').type('{esc}')
    cy.wait('@notificationList')

    cy.contains('Beta thread').should('be.visible')
    cy.contains('Alpha thread').should('not.exist')
  })

  it('keeps today’s rows under the Today filter and shows the day on an empty day', () => {
    cy.button('All dates').click()
    cy.button('Today').click()
    cy.wait('@notificationList')
    cy.button('Today').should('be.visible')
    cy.contains('Alpha thread').should('be.visible')
    cy.contains('Beta thread').should('be.visible')

    cy.window().then((win) => {
      win.localStorage.setItem(
        'gameplan:notificationFilters',
        JSON.stringify({
          communities: [],
          spaces: [],
          date: { kind: 'range', from: '2020-01-01', to: '2020-01-01' },
        }),
      )
    })
    cy.reload()
    cy.wait('@notificationList')
    cy.contains('1 January 2020').should('be.visible')
    cy.contains('Nothing here').should('be.visible')
  })
})
