// The "+ New discussion" entry point lives inside the community discussions list;
// the global /drafts page is a pure list. These tests drive the scoped composer and
// verify draft autosave + publish on the canonical scoped route.
import { resetData } from '../../support/seed'

describe('New discussion drafts', () => {
  let community: string
  let space: string
  // The auto-created space in the seeded community, and the only pickable option.
  const spaceTitle = 'General'

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = ids.community as string
      space = ids.space as string
    })
    cy.loginAs('member')
  })

  it('saves a draft while composing and publishes it into the chosen space', () => {
    // The community discussions list is the only "+ New discussion" entry point.
    cy.visit(`/g/community/${community}/discussions`)
    cy.button('Add new').click()
    cy.url().should('include', `/community/${community}/new-discussion`)

    cy.contains('New Discussion').should('exist')
    cy.get('textarea[placeholder="Title"]').should('exist')
    cy.get('[contenteditable=true]').should('exist')

    // Watch draft autosaves so each step waits for the content to actually reach the
    // server, rather than a fixed delay that races the autosave debounce (the row is
    // created on space-select; the typed content lands on a later save).
    const draftContent = 'This is my draft content that should be saved.'
    const updatedContent = 'This is my updated draft content. Ready to publish!'
    let draftContentSaved = false
    let updatedContentSaved = false
    cy.intercept('POST', '**/api/method/frappe.client.*', (req) => {
      const body = JSON.stringify(req.body ?? {})
      if (body.includes(draftContent)) draftContentSaved = true
      if (body.includes(updatedContent)) updatedContentSaved = true
    })

    // Create the draft. A draft is only persisted once a space is chosen.
    cy.get('textarea[placeholder="Title"]').type('My Draft Discussion{enter}')
    cy.get('[contenteditable=true]').click().type(draftContent)
    cy.contains('button[aria-haspopup="listbox"]', 'Select Space').click({ force: true })
    cy.get('[role="option"]').contains(spaceTitle).click()
    // Retries until an autosave carrying the content has completed.
    cy.wrap(null).should(() => expect(draftContentSaved, 'draft content autosaved').to.be.true)

    // The draft shows up on the global Drafts list.
    cy.visit('/g/drafts')
    cy.contains('My Draft Discussion').should('exist')
    cy.contains(draftContent).should('exist')

    // Reopen the draft and edit it.
    cy.contains('My Draft Discussion').click()
    cy.get('textarea[placeholder="Title"]').should('have.value', 'My Draft Discussion')
    cy.get('[contenteditable=true]').click().clear().type(updatedContent)
    // Retries until the edit has been autosaved, so Publish cannot race the debounce.
    cy.wrap(null).should(() => expect(updatedContentSaved, 'draft edit autosaved').to.be.true)

    // Publish lands on the canonical scoped Discussion route.
    cy.button('Publish').click()
    cy.url().should('include', `/community/${community}/space/${space}/discussion/`)
    cy.contains('My Draft Discussion').should('exist')
    cy.contains(updatedContent).should('exist')

    // The published draft is gone from the Drafts list.
    cy.visit('/g/drafts')
    cy.contains('My Draft Discussion').should('not.exist')
  })

  it('shows the publish button on the mobile composer', () => {
    cy.viewport('iphone-6')
    cy.visit(`/g/community/${community}/new-discussion`)

    cy.contains('New Discussion').should('exist')
    cy.button('Publish').should('be.visible')
  })
})
