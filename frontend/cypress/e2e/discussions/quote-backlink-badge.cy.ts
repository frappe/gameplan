// When a comment quotes a passage of the post, the post shows a "quoted by" badge
// in the lane to the right of the text. The badge is absolutely positioned past the
// content column, so it must neither make the post scroll sideways nor land inside
// a table cell, where it would cover the next cell or scroll the table.
import { resetData } from '../../support/seed'

const PARAGRAPH_PASSAGE = 'The rollout starts with the search team'
const CELL_PASSAGE = 'Shipped in the last sprint'

// The table's last column holds the quoted cell, so a badge anchored inside that
// cell would push past the table's right edge.
const POST_CONTENT = [
  `<p>${PARAGRAPH_PASSAGE} and then moves to everyone else.</p>`,
  '<table><tbody>',
  '<tr><th><p>Area</p></th><th><p>Owner</p></th><th><p>Status</p></th></tr>',
  `<tr><td><p>Search</p></td><td><p>Platform</p></td><td><p>${CELL_PASSAGE}</p></td></tr>`,
  '</tbody></table>',
].join('')

const richQuote = (discussion: string, author: string, text: string) =>
  `<blockquote data-author="${author}" data-rich-quote-id="discussion:${discussion}"><p>${text}</p></blockquote>`

describe('Quoted-by badge', () => {
  let community: string
  let space: string
  let discussion: string
  let discussionSlug: string

  beforeEach(() => {
    // The badge only shows from `sm` up, and needs room for the right-hand lane.
    cy.viewport(1440, 900)

    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
      discussionSlug = String(ids.discussion_slug)

      // resetData leaves an Administrator session, which may rewrite the seeded post.
      cy.request({
        method: 'PUT',
        url: `/api/v2/document/GP%20Discussion/${discussion}`,
        body: { content: POST_CONTENT },
      })

      // Both quotes go in through the API, before the first `cy.visit`, which keeps
      // `loginAs` safe. Composing a quote is not what this spec is about.
      cy.loginAs('secondMember')
      cy.request({
        method: 'POST',
        url: '/api/v2/document/GP%20Comment',
        body: {
          reference_doctype: 'GP Discussion',
          reference_name: discussion,
          content:
            richQuote(discussion, 'member@example.com', PARAGRAPH_PASSAGE) +
            richQuote(discussion, 'member@example.com', CELL_PASSAGE) +
            '<p>Two passages worth a reply</p>',
        },
      })
      cy.loginAs('member')
    })
  })

  const postContent = () => cy.contains('.ProseMirror p', PARAGRAPH_PASSAGE).closest('.ProseMirror')

  it('keeps the badges in the right lane without scrolling the post or the table', () => {
    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${discussionSlug}`)
    // The first render of the post and its comments can take longer than the 4s
    // default on a dev server.
    cy.contains('Two passages worth a reply', { timeout: 12000 }).should('be.visible')

    // The revisions dialog is a lazy chunk, and its styles once turned every editor
    // into a scroll container. Open and close it so those styles are on the page
    // before anything is measured, instead of racing the chunk.
    cy.selectDropdownOption('Discussion Options', 'Revisions')
    cy.get('[role="dialog"]').should('be.visible')
    cy.get('body').type('{esc}')
    cy.get('[role="dialog"]').should('not.exist')

    postContent().find('[data-quote-backlink-widget]').should('have.length', 2)
    postContent()
      .find('[data-quote-backlink-widget]')
      .each(($badge) => {
        cy.wrap($badge).should('be.visible')
        // A cell is position: relative, so a badge inside one resolves against the
        // cell instead of the content column.
        expect($badge.closest('td, th'), 'badge inside a table cell').to.have.length(0)
      })

    // The post must not become a horizontal scroll container for the badge. Its
    // scrollWidth counts the badge even while overflow is visible, so try to scroll
    // instead: a post that is not a scroll container ignores scrollLeft.
    postContent().should(($content) => {
      const el = $content[0]
      el.scrollLeft = el.scrollWidth
      expect(el.scrollLeft, 'post scrollLeft').to.equal(0)
    })

    // Nor may the table's own scroll wrapper grow to fit a badge.
    postContent()
      .find('.tableWrapper')
      .should('have.length', 1)
      .should(($wrapper) => {
        const el = $wrapper[0]
        expect(el.scrollWidth, 'table wrapper scrollWidth').to.be.at.most(el.clientWidth)
      })
  })
})
