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

  function createStoredDraft() {
    cy.visit(`/g/community/${community}/new-discussion`)
    cy.get('textarea[placeholder="Title"]').type('Stored Draft Title')
    cy.get('[contenteditable=true]').click().type('Stored draft body.')
    cy.contains('button[aria-haspopup="listbox"]', 'Select Space').click()
    cy.get('[role="option"]').contains(spaceTitle).click()
    cy.url().should('include', 'draft=')
  }

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
    cy.contains('button[aria-haspopup="listbox"]', 'Select Space').click()
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

  it('blocks editing while a saved draft is loading', () => {
    createStoredDraft()
    cy.intercept('POST', '**/api/method/frappe.client.get', (req) => {
      req.continue((res) => res.setDelay(3000))
    }).as('draftFetch')

    cy.url().then((composerUrl) => {
      cy.visit(composerUrl)
      cy.contains('[role="status"]', 'Loading draft…').should('be.visible')
      cy.get('textarea[placeholder="Title"]').should('be.disabled')
      cy.get('[aria-label="Discussion content"]').should('have.attr', 'contenteditable', 'false')
      cy.contains('button[aria-haspopup="listbox"]', spaceTitle).should('be.disabled')

      cy.wait('@draftFetch')
      cy.contains('[role="status"]', 'Loading draft…').should('not.exist')
      cy.get('textarea[placeholder="Title"]')
        .should('be.enabled')
        .and('have.value', 'Stored Draft Title')
      cy.get('[aria-label="Discussion content"]').should('have.attr', 'contenteditable', 'true')
      cy.contains('button[aria-haspopup="listbox"]', spaceTitle).should('be.enabled')
      cy.contains('Stored draft body.').should('exist')
    })
  })

  it('allows editing when a saved draft fails to load', () => {
    createStoredDraft()
    cy.intercept('POST', '**/api/method/frappe.client.get', {
      statusCode: 500,
      delay: 500,
      body: { exception: 'Draft lookup failed' },
    }).as('failedDraftFetch')

    cy.url().then((composerUrl) => {
      cy.visit(composerUrl)
      cy.contains('[role="status"]', 'Loading draft…').should('be.visible')
      cy.get('textarea[placeholder="Title"]').should('be.disabled')
      cy.get('[aria-label="Discussion content"]').should('have.attr', 'contenteditable', 'false')
      cy.contains('button[aria-haspopup="listbox"]', spaceTitle).should('be.disabled')

      cy.wait('@failedDraftFetch')
      cy.contains('[role="status"]', 'Loading draft…').should('not.exist')
      cy.get('textarea[placeholder="Title"]')
        .should('be.enabled')
        .type(' after failure')
        .should('have.value', 'Stored Draft Title after failure')
      cy.get('[aria-label="Discussion content"]')
        .should('have.attr', 'contenteditable', 'true')
        .click()
        .type(' Still editable.')
      cy.contains('button[aria-haspopup="listbox"]', spaceTitle).should('be.enabled')
      cy.contains('Stored draft body. Still editable.').should('exist')
    })
  })

  it('publishes an edit that lands while the last draft save is in flight', () => {
    createStoredDraft()
    // Hold every draft save open long enough to type into the composer while the publish
    // is waiting on one. A save only covers the snapshot it was built from, so the draft
    // is dirty again the moment it returns — with nothing actually failing.
    cy.intercept('POST', '**/api/method/frappe.client.set_value', (req) => {
      req.continue((res) => res.setDelay(1500))
    }).as('draftSave')

    cy.get('[contenteditable=true]').click().type(' First edit.')
    cy.button('Publish').click()
    cy.get('[contenteditable=true]').type(' Late edit.')

    cy.url({ timeout: 20000 }).should(
      'include',
      `/community/${community}/space/${space}/discussion/`,
    )
    cy.contains('Late edit.').should('exist')
  })

  it('reports a failed publish to the server', () => {
    createStoredDraft()
    cy.intercept(
      'POST',
      '**/api/method/gameplan.gameplan.doctype.gp_draft.gp_draft.publish_draft',
      { statusCode: 500, body: { exception: 'PublishError: no' } },
    ).as('failedPublish')
    cy.intercept('POST', '**/api/method/gameplan.api.log_client_error').as('errorReport')

    cy.button('Publish').click()

    cy.wait('@failedPublish')
    cy.wait('@errorReport').its('request.body.context.action').should('eq', 'publish-discussion')
    // Still on the composer, with the draft intact and the button clickable again.
    cy.url().should('include', 'new-discussion')
    cy.button('Publish').should('be.enabled')
  })

  it('shows the publish button on the mobile composer', () => {
    cy.viewport('iphone-6')
    cy.visit(`/g/community/${community}/new-discussion`)

    cy.contains('New Discussion').should('exist')
    cy.button('Publish').should('be.visible')
  })
})
