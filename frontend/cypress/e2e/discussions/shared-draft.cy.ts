// A new-discussion draft is readable by anyone holding its `?draft=` link, but only its
// owner can change it. Opening someone else's draft must stay read-only and must never
// save a copy for the reader — not even when the editor normalizes the content on first
// render, which it does for images and code blocks.
import { resetData } from '../../support/seed'
import { personas } from '../../support/personas'

describe('Shared draft links', () => {
  const sharedTitle = 'Member draft shared by link'
  const sharedCode = 'const shared = true'
  // An image with an alignment and a code block: TipTap rewrites both on first render,
  // so the editor emits a change the reader never made.
  const sharedContent = [
    '<p>Shared draft body.</p>',
    `<pre><code>${sharedCode}</code></pre>`,
    '<p><img src="/files/shared-draft.png" width="245" height="431" data-align="center">After image</p>',
  ].join('')

  let community: string
  let space: string

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
    })
  })

  /** The acting user's own GP Draft rows. The list endpoint is owner-scoped on the server. */
  function myDraftRows() {
    return cy
      .request(`/api/v2/document/GP%20Draft?fields=${encodeURIComponent('["name","title"]')}`)
      .its('body.data')
  }

  /** The editor's root. Code blocks render their own `contenteditable` nodes inside it. */
  const editorRoot = () => cy.get('.ProseMirror')

  /** IndexedDB draft records that hold the shared draft's content. */
  function localCopiesOfSharedDraft() {
    return cy.window().then(
      (win) =>
        new Cypress.Promise<number>((resolve, reject) => {
          const open = win.indexedDB.open('gameplan-drafts')
          open.onerror = () => reject(open.error)
          open.onsuccess = () => {
            const db = open.result
            if (!db.objectStoreNames.contains('records')) return resolve(0)
            const all = db.transaction('records').objectStore('records').getAll()
            all.onerror = () => reject(all.error)
            all.onsuccess = () =>
              resolve(
                all.result.filter((record) => record.payload?.content?.includes(sharedCode))
                  .length,
              )
          }
        }),
    )
  }

  it("opens another member's draft read-only and never saves a copy of it", () => {
    // Any draft write by the reader is the bug, whether it inserts or updates.
    const writes: string[] = []

    cy.loginAs('member')
    cy.request({
      method: 'POST',
      url: '/api/v2/document/GP%20Draft',
      body: {
        type: 'Discussion',
        mode: 'New',
        title: sharedTitle,
        content: sharedContent,
        project: space,
      },
    })
      .its('body.data.name')
      .then((draftName) => {
        cy.clearCookies()
        cy.loginAs('secondMember')
        cy.intercept(/\/api\/v2\/document\/GP%20Draft/, (req) => {
          if (req.method !== 'GET') writes.push(`${req.method} ${req.url}`)
        })

        cy.visit(`/g/community/${community}/new-discussion?draft=${draftName}`)
      })

    // The reader sees the owner's content.
    cy.get('textarea[placeholder="Title"]').should('have.value', sharedTitle)
    editorRoot().should('contain.text', sharedCode)

    // Outlast the autosave debounce, then confirm nothing was saved anywhere.
    cy.wait(3000)
    cy.wrap(writes).should('deep.equal', [])
    myDraftRows().should('have.length', 0)
    localCopiesOfSharedDraft().should('eq', 0)

    // Read-only, attributed to the owner, and with nothing to publish or delete.
    cy.contains(`${personas.member.displayName}'s draft`).should('be.visible')
    cy.get('textarea[placeholder="Title"]').should('be.disabled')
    editorRoot().should('have.attr', 'contenteditable', 'false')
    cy.get('button[aria-haspopup="listbox"]:visible').should('be.disabled')
    cy.get('button:contains("Publish")').should('not.exist')
    cy.get('button[aria-label="Delete draft"]').should('not.exist')

    // Leaving the page must not push anything either.
    cy.visit('/g/drafts')
    cy.contains(sharedTitle).should('not.exist')
    cy.wrap(writes).should('deep.equal', [])
    myDraftRows().should('have.length', 0)
  })

  it('still autosaves a draft of your own', () => {
    cy.loginAs('secondMember')
    cy.visit(`/g/community/${community}/new-discussion`)

    cy.contains(`${personas.member.displayName}'s draft`).should('not.exist')
    cy.get('textarea[placeholder="Title"]').should('not.be.disabled').type('My own draft')
    cy.get('[contenteditable=true]').click().type('Typed by its owner.')
    cy.contains('button[aria-haspopup="listbox"]', 'Select Space').click()
    cy.get('[role="option"]').contains('General').click()
    cy.url().should('include', 'draft=')
    cy.button('Publish').should('not.be.disabled')

    myDraftRows().should('have.length', 1)
  })
})
