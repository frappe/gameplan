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
  let releaseLookup: (() => void) | undefined
  let releaseReplacement: (() => void) | undefined

  beforeEach(() => {
    resetData('space_with_discussion').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
      discussion = String(ids.discussion)
      slug = String(ids.discussion_slug)
    })
    cy.loginAs('member')
  })

  afterEach(() => {
    releaseLookup?.()
    releaseLookup = undefined
    releaseReplacement?.()
    releaseReplacement = undefined
    cy.window().then((win) => {
      delete (win.navigator as unknown as { onLine?: boolean }).onLine
      win.dispatchEvent(new win.Event('online'))
    })
  })

  it('retries only the saved draft after a mixed deletion fails', () => {
    const local = 'aaaaaaaaaaaaaaaaaaaa'
    cy.request('POST', '/api/v2/document/GP%20Draft', {
      type: 'Discussion',
      mode: 'New',
      project: space,
      title: 'Saved selection',
      content: '<p>Server copy</p>',
    })
      .its('body.data.name')
      .then((saved) => {
        cy.visit('/g/drafts')
        cy.contains('a', 'Saved selection').should('be.visible')
        cy.window().then((win) => win.navigator.locks.request('gp-draft-recovery', () => {}))
        localRecord((store) =>
          store.put(
            {
              key: local,
              user: 'member@example.com',
              identity: { type: 'Discussion', mode: 'New' },
              payload: { title: 'Local selection', content: '<p>Local copy</p>', project: space },
              saved: false,
              updatedAt: Date.now(),
              syncedAt: null,
            },
            local,
          ),
        )
        cy.window().then((win) => {
          const channel = new win.BroadcastChannel('gameplan-drafts')
          channel.postMessage({ key: local })
          channel.close()
        })
        cy.contains('a', 'Local selection').should('be.visible')
        cy.get('button[aria-label="Draft actions"]').filter(':visible').click()
        cy.contains('[role="menuitem"]', 'Select drafts').click()
        for (const title of ['Local selection', 'Saved selection'])
          cy.contains('a', title).find('[data-slot="list-row-checkbox"]').click()
        cy.intercept(
          { method: 'POST', url: '**/api/v2/method/GP%20Draft/bulk_delete', times: 1 },
          (req) => {
            expect(req.body.names).to.deep.eq([saved])
            req.reply({ statusCode: 503 })
          },
        ).as('failedBulkDelete')
        cy.button('Delete 2 drafts').click()
        cy.get('[role="dialog"]').contains('button', 'Delete').click()
        cy.wait('@failedBulkDelete')
        cy.contains('Draft deleted').should('exist')
        cy.contains('1 draft could not be deleted').should('be.visible')
        cy.contains('a', 'Local selection').should('not.exist')
        localRecord((store) => store.get(local)).then(
          ({ record }) => expect(record).to.be.undefined,
        )
        cy.intercept('POST', '**/api/v2/method/GP%20Draft/bulk_delete', (req) => {
          expect(req.body.names).to.deep.eq([saved])
          req.continue()
        }).as('retryBulkDelete')
        cy.button('Delete 1 draft').click()
        cy.get('[role="dialog"]').contains('button', 'Delete').click()
        cy.wait('@retryBulkDelete')
        cy.contains('No drafts').should('be.visible')
      })
  })

  it('shares a reply when both tabs open before either starts typing', () => {
    cy.intercept('POST', CREATE).as('create')
    cy.then(() =>
      cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`),
    )
    cy.button('Add a comment').click()
    cy.get('.ProseMirror').last().should('have.text', '')
    cy.document().then((doc) => {
      const tab = doc.createElement('iframe')
      tab.id = 'reply-tab'
      tab.src = doc.location.href
      tab.style.cssText = 'width:1000px;height:600px'
      doc.body.appendChild(tab)
    })
    const otherEditor = () =>
      cy
        .get<HTMLIFrameElement>('#reply-tab')
        .its('0.contentDocument.body')
        .find('.ProseMirror')
        .last()
    otherEditor().should('have.text', '')

    cy.get('.ProseMirror').last().click({ force: true }).type('Shared live reply', { force: true })
    cy.wait('@create')
    otherEditor().should('contain.text', 'Shared live reply')
    otherEditor().click({ force: true }).type(' from the other tab', { force: true })
    cy.get('.ProseMirror').last().should('contain.text', 'Shared live reply from the other tab')
    cy.intercept('PUT', '**/api/v2/document/GP%20Draft/*', (req) => {
      if (req.body.content?.includes('later edit')) req.alias = 'laterEdit'
    })
    otherEditor().click({ force: true }).type('{selectall}{backspace}', { force: true })
    cy.get('.ProseMirror').last().click({ force: true }).type(' later edit', { force: true })
    cy.wait('@laterEdit')
    otherEditor().should('have.text', '')
    cy.request('/api/v2/document/GP%20Draft?fields=["name"]')
      .its('body.data')
      .should('have.length', 1)
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

  it('keeps an open editor and edits made while another tab recovers its draft', () => {
    let lookupPending = false
    let replacementPending = false
    cy.intercept('POST', CREATE).as('create')
    cy.then(() =>
      cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`),
    )
    cy.button('Add a comment').click()
    cy.get('.ProseMirror').last().click().type('My saved reply')
    cy.wait('@create').its('request.body.name').as('original')
    // Only this tab is offline; the second document can still recover stored drafts.
    cy.window().then((win) => {
      Object.defineProperty(win.navigator, 'onLine', { configurable: true, get: () => false })
      win.dispatchEvent(new win.Event('offline'))
    })
    cy.get('.ProseMirror').last().click().type(' with unsynced edits')
    cy.get<string>('@original').then((name) =>
      localRecord((store) => store.get(name))
        .its('record.payload.content')
        .should('include', 'unsynced edits'),
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
      cy.request({ method: 'POST', url: FIND, headers, body: identity })
    })
    cy.intercept('POST', '**/gameplan.gameplan.doctype.gp_draft.gp_draft.find_my_draft', (req) => {
      req.continue(
        () =>
          new Cypress.Promise<void>((resolve) => {
            lookupPending = true
            releaseLookup = resolve
          }),
      )
    })
    cy.get<string>('@original').then((original) =>
      cy.window().then((win) => {
        const get = win.IDBObjectStore.prototype.get
        win.IDBObjectStore.prototype.get = function (key) {
          const request = get.call(this, key)
          if (this.name === 'records' && key !== original && !replacementPending) {
            request.addEventListener(
              'success',
              (event) => {
                event.stopImmediatePropagation()
                replacementPending = true
                releaseReplacement = () => request.onsuccess?.call(request, event)
              },
              { once: true },
            )
          }
          return request
        }
      }),
    )
    // A second same-origin document has its own composer state and BroadcastChannel.
    cy.document().then((doc) => {
      const tab = doc.createElement('iframe')
      tab.src = '/g/drafts'
      doc.body.appendChild(tab)
    })
    cy.wrap(null).should(() => expect(lookupPending, 'recovery lookup pending').to.eq(true))
    cy.get('.ProseMirror').last().click().type(' plus newer tab edits')
    cy.get<string>('@original').then((name) =>
      localRecord((store) => store.get(name))
        .its('record.payload.content')
        .should('include', 'newer tab edits'),
    )
    cy.then(() => releaseLookup?.())
    cy.wait('@create', { timeout: 10000 }).then(({ request }) => {
      expect(request.body.content).to.include(
        'My saved reply with unsynced edits plus newer tab edits',
      )
      cy.get('@original').should('not.eq', request.body.name)
    })
    cy.wrap(null).should(() => expect(replacementPending, 'replacement read pending').to.eq(true))
    cy.get('.ProseMirror').last().click().type(' while loading the replacement')
    cy.get<string>('@original').then((name) =>
      localRecord((store) => store.get(name)).then(({ record }) => expect(record).to.be.undefined),
    )
    cy.then(() => releaseReplacement?.())
    cy.get('.ProseMirror')
      .last()
      .should(
        'contain.text',
        'My saved reply with unsynced edits plus newer tab edits while loading the replacement',
      )
    cy.get('.ProseMirror').last().click().type(' and continuing')
    localRecord((store) => store.getAll()).then(({ record }) => {
      expect(record.some((draft) => draft.payload.content.includes('and continuing'))).to.eq(true)
    })
    cy.contains('This draft was deleted').should('not.exist')
  })

  it('adopts newer recovered edits instead of overwriting them with an older open buffer', () => {
    const replacementKey = 'recoveredreplydraftaa'
    cy.intercept('POST', CREATE).as('create')
    cy.then(() =>
      cy.visit(`/g/community/${community}/space/${space}/discussion/${discussion}/${slug}`),
    )
    cy.button('Add a comment').click()
    cy.get('.ProseMirror').last().click().type('My saved reply')
    cy.wait('@create').its('request.body.name').as('original')
    cy.window().then((win) => {
      Object.defineProperty(win.navigator, 'onLine', { configurable: true, get: () => false })
      win.dispatchEvent(new win.Event('offline'))
    })
    cy.get('.ProseMirror').last().click().type(' with older unsynced edits')
    cy.get<string>('@original').then((original) => {
      // Another tab stored newer text, then recovery moved it while this editor stayed open.
      localRecord((store) => {
        const request = store.get(original)
        request.onsuccess = () => {
          const record = request.result
          store.put(
            {
              ...record,
              key: replacementKey,
              saved: false,
              updatedAt: record.updatedAt + 1,
              payload: { ...record.payload, content: '<p>Newer edits saved by another tab</p>' },
            },
            replacementKey,
          )
          store.delete(original)
        }
        return request
      })
      cy.window().then((win) => {
        const otherTab = new win.BroadcastChannel('gameplan-drafts')
        otherTab.postMessage({ key: original, replacementKey })
        otherTab.close()
      })
      cy.get('.ProseMirror').last().should('contain.text', 'Newer edits saved by another tab')
      localRecord((store) => store.get(replacementKey))
        .its('record.payload.content')
        .should('include', 'Newer edits saved by another tab')
      localRecord((store) => store.get(original)).then(
        ({ record }) => expect(record).to.be.undefined,
      )
    })
  })

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
