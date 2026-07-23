// Links from every surface must resolve into canonical
// `/community/:communityId/...` routes, and a space breadcrumb's root must point
// at the scoped space route rather than the global /spaces page.
import { resetData } from '../../support/seed'

describe('Community scoped links', () => {
  let community: string
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = ids.community as string
      space = ids.space as string
      discussion = ids.discussion as string
    })
    cy.loginAs('member')
    // A bookmark is per-user, not part of the world: create it as the persona who
    // will read it, so it shows up on their global /bookmarks page.
    cy.then(() => {
      cy.request('POST', `/api/v2/document/GP Discussion/${discussion}/method/add_bookmark`)
    })
  })

  it('opens a space from the community sidebar on the canonical scoped route', () => {
    // The community sidebar is the surface that links a space to its canonical
    // scoped route; the old global /spaces page is now the admin /configure
    // housekeeping view, which only renames/archives spaces.
    cy.visit(`/g/community/${community}/discussions`)
    cy.contains('a', 'Engineering').click()
    cy.url().should('include', `/community/${community}/space/${space}`)
  })

  it('opens a bookmarked discussion on a canonical scoped route', () => {
    cy.visit('/g/bookmarks')
    cy.contains('Welcome thread').click()
    cy.url().should('include', `/community/${community}/`)
    cy.url().should('include', `/discussion/${discussion}`)
  })

  it('points the space breadcrumb root at the canonical scoped space route, not /spaces', () => {
    cy.visit(`/g/community/${community}/space/${space}`)

    // The community title was intentionally removed from the space breadcrumbs;
    // the root crumb is now the space itself and links to its canonical scoped
    // route. It must not route back to the global /spaces page.
    cy.get('.space-breadcrumbs')
      .contains('a', 'Engineering')
      .should('have.attr', 'href')
      .and('include', `/community/${community}/space/${space}`)
      .and('not.include', '/spaces')
  })
})
