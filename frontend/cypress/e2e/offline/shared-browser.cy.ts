// A browser two people use: nothing one of them read may still be on the machine for the
// next. Covers the plain logout, and the switch that happens without one — a swapped
// cookie, `bench browse --sid`, a session that went stale in an old tab.
import { resetData } from '../../support/seed'
import { personas } from '../../support/personas'
import {
  CACHE_PREFIX,
  DRAFT_STORE,
  RESOURCE_STORE,
  cacheNamespace,
  secureOrigin,
} from '../../support/offline'

describe('A shared browser', () => {
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
  })

  /** Opens enough for the resource cache to hold this account's content. */
  const readSomething = () => {
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`)
    cy.contains('h1', 'Welcome thread').should('be.visible')
    cy.idbKeys().should('not.be.empty')
  }

  it('clears what the account read on logout, but keeps its drafts', () => {
    cy.loginAs('member')
    readSomething()

    // A draft is the one thing a logout keeps: the same person signing back in should
    // still find what they were writing.
    cy.button('Add a comment').click()
    cy.get('.ProseMirror').last().click().type('half-written reply')
    cy.idbKeys(DRAFT_STORE).should('not.be.empty')

    cy.iconButton('Account menu').click()
    cy.contains('[role="menuitem"]', 'Log out').click()
    cy.url({ timeout: 20000 }).should('include', '/login')

    cy.idbKeys(RESOURCE_STORE).should('be.empty')
    cy.idbKeys(DRAFT_STORE).should('not.be.empty')

    if (secureOrigin()) {
      // The worker's own buckets go too, bar the build files, which are the same for
      // everyone and hold nothing of the person who just left.
      cy.cacheNames().should((names) => {
        const mine = names.filter((n) => n.startsWith(`${CACHE_PREFIX}:`))
        expect(mine.filter((n) => !n.endsWith(':assets'))).to.be.empty
      })
    }
  })

  it('clears the previous account when a different one signs in without logging out', () => {
    cy.loginAs('member')
    readSomething()
    cy.lastSeenUser().should('eq', personas.member.email)

    cy.idbKeys().then((before) => {
      const theirs = before.filter((key) => key.startsWith(cacheNamespace(personas.member.email)))
      expect(theirs, "keys tagged with the first account's name").to.not.be.empty

      // No logout: just a different session, the way a swapped cookie arrives.
      cy.loginAs('secondMember')
      cy.visit('/g')
      cy.get('[data-slot="desktop-shell"]', { timeout: 40000 }).should('exist')

      cy.lastSeenUser().should('eq', personas.secondMember.email)
      cy.idbKeys().should((after) => {
        const survivors = after.filter((key) =>
          key.startsWith(cacheNamespace(personas.member.email)),
        )
        expect(survivors, "the first account's cached keys").to.be.empty
      })
    })
  })

  it('still detects the switch when the first session went stale first', () => {
    cy.loginAs('member')
    readSomething()
    cy.lastSeenUser().should('eq', personas.member.email)

    // The session expires and the app is opened signed-out. The marker has to survive
    // that, or the next sign-in looks like nobody was here before and skips the clear.
    cy.clearCookies()
    cy.visit('/g', { failOnStatusCode: false })
    cy.lastSeenUser().should('eq', personas.member.email)

    cy.loginAs('secondMember')
    cy.visit('/g')
    cy.get('[data-slot="desktop-shell"]', { timeout: 40000 }).should('exist')

    cy.lastSeenUser().should('eq', personas.secondMember.email)
    cy.idbKeys().should((after) => {
      const survivors = after.filter((key) => key.startsWith(cacheNamespace(personas.member.email)))
      expect(survivors, "the first account's cached keys").to.be.empty
    })
  })
})
