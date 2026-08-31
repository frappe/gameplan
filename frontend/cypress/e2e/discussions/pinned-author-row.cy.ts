// The pinned author row masks the content scrolling under it. A selected image draws
// its ring 4px outside its own box (`ring-2 ring-offset-2` in frappe-ui's media node
// view), and that box is already the full width of the content column. A row that
// stops at the column edge leaves the ring's two vertical edges visible above it,
// running up to the page header.
import { resetData } from '../../support/seed'

// ring-2 (2px) + ring-offset-2 (2px)
const RING_PX = 4

// Any asset the site already serves does: the node view lays the image out from the
// width/height attributes, so this fills the column like a real screenshot would. A
// `data:` src would be simpler but frappe's HTML sanitizer strips it on save.
const WIDE_IMAGE = '<img src="/assets/frappe/images/frappe-favicon.svg" width="1600" height="900">'

describe('Pinned author row', () => {
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
  })

  function assertRowOverhangs(dropdownLabel: string, scope: string) {
    cy.get(scope)
      .find(`button[aria-haspopup=menu][aria-label="${dropdownLabel}"]`)
      .parents('.sticky')
      .first()
      .then(($row) => {
        cy.get(scope)
          .find('img[src*="frappe-favicon"]')
          .then(($image) => {
            const row = $row[0].getBoundingClientRect()
            const image = $image[0].getBoundingClientRect()
            expect(row.left, 'row covers the ring on the left').to.be.at.most(image.left - RING_PX)
            expect(row.right, 'row covers the ring on the right').to.be.at.least(
              image.right + RING_PX,
            )
          })
      })
  }

  it('is wider than the content column, in the post and in a comment', () => {
    cy.request('PUT', `/api/v2/document/GP%20Discussion/${discussion}`, {
      content: `<p>Post content</p>${WIDE_IMAGE}`,
    })
    cy.request('POST', '/api/v2/document/GP%20Comment', {
      reference_doctype: 'GP Discussion',
      reference_name: discussion,
      content: `<p>Comment content</p>${WIDE_IMAGE}`,
    }).then(({ body }) => {
      const comment = `div[data-id="${body.data.name}"]`
      cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)

      cy.get(comment).should('exist')
      assertRowOverhangs('Discussion Options', '.discussion-container')
      assertRowOverhangs('Comment Options', comment)
    })
  })
})
