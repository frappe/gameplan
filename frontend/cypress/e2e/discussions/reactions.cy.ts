// Reacting is the smallest bit of participation in Gameplan: one click on the post,
// one on a reply. The point of this spec is that both survive a page reload — the
// reaction is stored on the server, not just painted optimistically in the client.
import { resetData } from '../../support/seed'

const POST_EMOJI = '👍'
const COMMENT_EMOJI = '💖'
// A quick-reaction emoji this spec never picks, so it only ever appears inside an
// open emoji grid — which makes it a reliable "is a picker still open?" probe.
const GRID_ONLY_EMOJI = '🤯'

describe('Reactions', () => {
  let community: string
  let space: string
  let discussion: string
  let discussionSlug: string
  let comment: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
      discussionSlug = String(ids.discussion_slug)

      // The scenario seeds a post but no reply, and this spec is about reacting, not
      // about composing one (comments/comment-actions.cy.ts owns that). So member2's
      // reply goes in through the API — still before the first `cy.visit`, which is
      // what keeps `loginAs` safe and the request free of a session CSRF token.
      cy.loginAs('secondMember')
      cy.request({
        method: 'POST',
        url: '/api/v2/document/GP%20Comment',
        body: {
          reference_doctype: 'GP Discussion',
          reference_name: discussion,
          content: '<p>A reply worth reacting to</p>',
        },
      }).then((response) => {
        comment = String(response.body.data.name)
      })
      cy.loginAs('member')
    })
  })

  const commentSelector = () => `div[data-id="${comment}"]`

  // Reactions render one widget per post, in document order: the discussion's own
  // widget sits above the comments, so the first "Add a reaction" button is the post's.
  const postReactionPicker = () => cy.get('button[aria-label="Add a reaction"]').first()

  // The picker is a portalled hover card, so it cannot be scoped to the thing it
  // belongs to. Using a different emoji per target keeps the visible emoji button
  // unambiguous.
  const pickEmoji = (emoji: string) => cy.get(`button:contains("${emoji}"):visible`).click()

  // A hover card stays open as long as the pointer rests on it, and Cypress leaves its
  // synthetic pointer wherever it last clicked. Dismiss the post's picker before
  // opening the reply's, or both emoji grids are on screen and the next pick is
  // ambiguous.
  const dismissPicker = () => {
    cy.get('body').type('{esc}')
    cy.get(`button:contains("${GRID_ONLY_EMOJI}")`).should('not.exist')
  }

  it('reacts to a discussion and to a comment, and both survive a reload', () => {
    cy.intercept('POST', `/api/v2/document/GP%20Discussion/${discussion}/method/react`).as(
      'reactToPost',
    )
    cy.intercept('POST', '/api/v2/document/GP%20Comment/*/method/react').as('reactToComment')

    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${discussionSlug}`)
    cy.contains('h1', 'Welcome thread').should('be.visible')
    cy.contains('A reply worth reacting to').should('be.visible')

    // React to the post.
    postReactionPicker().click()
    pickEmoji(POST_EMOJI)
    cy.wait('@reactToPost')
    dismissPicker()

    // React to member2's reply.
    cy.get(commentSelector()).find('button[aria-label="Add a reaction"]').click()
    pickEmoji(COMMENT_EMOJI)
    cy.wait('@reactToComment')
    dismissPicker()

    // The pill separates emoji and count with a non-breaking space, so match on a
    // regex (\s covers U+00A0) rather than a literal space.
    const postPill = new RegExp(`${POST_EMOJI}\\s*1`)
    const commentPill = new RegExp(`${COMMENT_EMOJI}\\s*1`)

    const assertBothReactionsShown = () => {
      cy.get(commentSelector()).contains('button', commentPill).should('exist')
      // The post's reaction stays on the post; the reply never picks it up.
      cy.get(commentSelector()).contains('button', postPill).should('not.exist')
      cy.contains('button', postPill).should('exist')
    }

    assertBothReactionsShown()

    cy.reload()
    cy.contains('h1', 'Welcome thread').should('be.visible')
    assertBothReactionsShown()
  })
})
