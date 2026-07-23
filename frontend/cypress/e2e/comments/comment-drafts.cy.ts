import { resetData } from '../../support/seed'

// A half-written reply auto-saves as a comment draft (GP Draft, type=Comment). These
// tests verify it surfaces on the global Drafts list and that opening it lands on the
// discussion with the reply composer restored — the feature added alongside the
// new-discussion drafts that the list already showed.
describe('Comment drafts', () => {
  const discussionTitle = 'Welcome thread'
  const replyText = 'This is a half-written reply that should be saved as a draft.'

  let community: string
  let space: string
  let discussion: string

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
    })
    cy.loginAs('member')
  })

  // The Drafts list fetches via get_my_drafts; waiting on it avoids a detached-element
  // race where the cached render is replaced by the network render mid-command.
  // Match anywhere in the URL via regex — the method path segment is dotted
  // (…gp_draft.gp_draft.get_my_drafts), which a minimatch glob can't target cleanly.
  const interceptDrafts = () => cy.intercept(/get_my_drafts/).as('getDrafts')

  it('shows a comment draft in the list and reopens it with the composer restored', () => {
    // The draft is created lazily on the first push via frappe.client.insert.
    cy.intercept('POST', '/api/method/frappe.client.insert').as('draftInsert')

    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)

    // Start a reply but never submit it — typing alone auto-saves a comment draft.
    cy.button('Add a comment').click()
    cy.get('[contenteditable=true]').should('be.visible').click().type(replyText)
    cy.wait('@draftInsert') // server row created

    // The reply now appears on the global Drafts list, labelled as a reply and showing
    // the parent discussion's title plus the reply preview.
    interceptDrafts()
    cy.visit('/g/drafts')
    cy.wait('@getDrafts') // let the list settle before asserting/clicking
    cy.contains(discussionTitle).should('exist')
    cy.contains(replyText).should('exist')
    cy.get('.lucide-reply').should('exist')

    // Opening it lands on the discussion with the composer restored.
    cy.contains(replyText).click()
    cy.url().should('include', `/space/${space}/discussion/${discussion}`)
    cy.get('[contenteditable=true]').should('be.visible').should('contain.text', replyText)
  })

  it('removes the comment draft from the list once submitted', () => {
    cy.intercept('POST', '/api/method/frappe.client.insert').as('draftInsert')
    cy.intercept('POST', '/api/v2/document/GP%20Comment').as('comment')

    cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}`)

    cy.button('Add a comment').click()
    cy.get('[contenteditable=true]').should('be.visible').click().type(replyText)
    cy.wait('@draftInsert')

    // Posting the reply commits the draft, which deletes the GP Draft row.
    cy.button('Submit').click()
    cy.wait('@comment')

    interceptDrafts()
    cy.visit('/g/drafts')
    cy.wait('@getDrafts')
    cy.contains(replyText).should('not.exist')
  })
})
