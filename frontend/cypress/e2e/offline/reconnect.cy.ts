// Coming back: what was missed while the connection was gone arrives on its own, without
// the reader having to reload.
//
// The change is made by someone else in a session of their own (`requestAsUser` runs in
// Node, outside the browser's cookie jar), because a change made in this browser would be
// applied locally and prove nothing about refetching.
import { resetData } from '../../support/seed'
import { personas } from '../../support/personas'

describe('Coming back online', () => {
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

  it('picks up a reply posted while the connection was down', () => {
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`)
    cy.contains('h1', 'Welcome thread').should('be.visible')

    cy.goOffline()
    cy.contains('[role="status"]', 'Offline').should('be.visible')

    cy.task('requestAsUser', {
      user: personas.secondMember.email,
      password: personas.secondMember.password,
      path: '/api/v2/document/GP Comment',
      body: {
        reference_doctype: 'GP Discussion',
        reference_name: discussion,
        content: '<p>posted while the reader was offline</p>',
      },
    })

    // Still offline, so it cannot be here yet.
    cy.contains('posted while the reader was offline').should('not.exist')

    cy.goOnline()
    // No reload: the timeline revalidates itself once the connection returns.
    cy.contains('posted while the reader was offline', { timeout: 30000 }).should('be.visible')
  })

  it('keeps the reader where they were rather than jumping to the newest reply', () => {
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`)
    cy.contains('h1', 'Welcome thread').should('be.visible')

    // The timeline positions itself once per discussion. A reconnect reload used to
    // re-run that and throw the reader to the bottom of the thread.
    cy.get('[data-slot="scroll-area-viewport"]')
      .last()
      .then(($el) => {
        const el = $el[0]
        el.scrollTo({ top: Math.floor(el.scrollHeight / 3) })
        const before = el.scrollTop

        cy.goOffline()
        cy.contains('[role="status"]', 'Offline').should('be.visible')
        cy.goOnline()
        cy.get('[role="status"]').should('not.exist')

        // Give the revalidation time to land before reading the position back.
        cy.wait(3000)
        cy.wrap(null).should(() => {
          expect(Math.abs(el.scrollTop - before), 'scroll position after reconnect').to.be.lessThan(
            40,
          )
        })
      })
  })
})
