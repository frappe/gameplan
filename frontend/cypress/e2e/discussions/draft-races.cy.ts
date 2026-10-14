import { resetData } from '../../support/seed'

const CREATE = '**/api/v2/document/GP%20Draft'
const FIND = '/api/v2/method/gameplan.gameplan.doctype.gp_draft.gp_draft.find_my_draft'

function localRecord<T>(run: (store: IDBObjectStore) => IDBRequest<T>) {
  return cy.window().then(
    (win) =>
      new Cypress.Promise<{ record: T }>((resolve, reject) => {
        const opening = win.indexedDB.open('gameplan-drafts')
        opening.onerror = () => reject(opening.error)
        opening.onsuccess = () => {
          const db = opening.result
          const transaction = db.transaction('records', 'readwrite')
          const request = run(transaction.objectStore('records'))
          transaction.oncomplete = () => {
            db.close()
            resolve({ record: request.result })
          }
          transaction.onerror = () => {
            db.close()
            reject(transaction.error)
          }
        }
      }),
  )
}

describe('Draft saves across devices and tabs', () => {
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

  for (const resume of ['reload', 'reconnect', 'draft recovery']) {
    it(`preserves displaced reply edits on ${resume}`, () => {
      cy.intercept('POST', CREATE).as('create')
      cy.then(() =>
        cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`),
      )
      cy.button('Add a comment').click()
      cy.get('.ProseMirror').last().click().type('My saved reply')
      cy.wait('@create').its('request.body.name').as('original')
      cy.goOffline()
      cy.get('.ProseMirror').last().click().type(' with unsynced edits')
      cy.get<string>('@original').then((name) =>
        localRecord((store) => store.get(name)).then(({ record }) => {
          expect(record.saved).to.eq(true)
          expect(record.payload.content).to.include('with unsynced edits')
          expect(record.updatedAt).to.be.greaterThan(record.syncedAt)
        }),
      )

      cy.window().then((win) => {
        const headers = {
          'X-Frappe-CSRF-Token': (win as unknown as { csrf_token: string }).csrf_token,
        }
        const identity = {
          type: 'Comment',
          mode: 'New',
          reference_doctype: 'GP Discussion',
          reference_name: discussion,
        }
        cy.request({
          method: 'POST',
          url: '/api/v2/document/GP Draft',
          headers,
          body: { ...identity, content: '<p>Other device reply</p>' },
        })
          .its('body.data.name')
          .as('other')
        cy.request({ method: 'POST', url: FIND, headers, body: identity })
          .its('body.data.name')
          .then((name) => cy.get('@other').should('eq', name))
        if (resume !== 'reconnect') {
          cy.then(() => {
            win.location.href = 'about:blank'
          })
        }
      })
      if (resume !== 'reconnect') cy.window().its('location.href').should('eq', 'about:blank')
      cy.goOnline()
      if (resume === 'reload') {
        cy.then(() =>
          cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`),
        )
      } else if (resume === 'draft recovery') {
        cy.visit('/g/drafts')
      }
      cy.wait('@create', { timeout: 10000 }).then(({ request }) => {
        expect(request.body.content).to.include('with unsynced edits')
        cy.get('@original').should('not.eq', request.body.name)
        cy.get('@other').should('not.eq', request.body.name)
      })
      if (resume === 'draft recovery') {
        cy.then(() =>
          cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`),
        )
      }
      cy.get('.ProseMirror').last().should('contain.text', 'My saved reply with unsynced edits')
      cy.contains('This draft was deleted').should('not.exist')
    })
  }

  it('does not upload a local draft deleted while its save waits for a lock', () => {
    let creates = 0
    let release: (() => void) | undefined
    cy.intercept('POST', CREATE, () => {
      creates++
    })
    cy.then(() => cy.visit(`/g/community/${community}/new-discussion?spaceId=${space}`))
    cy.get('textarea[placeholder="Title"]').should('be.visible')
    cy.goOffline()
    cy.get('textarea[placeholder="Title"]').type('Deleted before upload')
    cy.location('search').should('match', /draft=[a-z0-9]{20}/)
    cy.location('search').then((search) => {
      const name = new URLSearchParams(search).get('draft')!
      const lock = `gp-draft:${name}`
      cy.window().then(
        (win) =>
          new Cypress.Promise<void>((acquired) => {
            void win.navigator.locks.request(lock, () => {
              acquired()
              return new Promise<void>((resolve) => (release = resolve))
            })
          }),
      )
      cy.goOnline()
      cy.window().then(
        { timeout: 10000 },
        (win) =>
          new Cypress.Promise<void>((queued) => {
            const poll = async () => {
              const { pending } = await win.navigator.locks.query()
              if (pending?.some((entry) => entry.name === lock)) queued()
              else win.setTimeout(poll, 20)
            }
            void poll()
          }),
      )
      localRecord((store) => store.delete(name))
      cy.then(() => release?.())
      // This barrier runs after the queued save has finished, including its network leg.
      cy.window().then((win) => win.navigator.locks.request(lock, () => {}))
      cy.then(() => expect(creates, 'uploads after deletion').to.eq(0))
      localRecord((store) => store.get(name)).then(({ record }) => {
        expect(record).to.be.undefined
      })
    })
  })
})
