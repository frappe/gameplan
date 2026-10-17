// Download for offline: keeping a window of discussions on the device, including ones
// this browser has never opened, and keeping that up to date cheaply.
//
// The request counts matter as much as the content — the whole feature is only acceptable
// if an up-to-date device costs the server one query.
import { resetData } from '../../support/seed'
import { personas } from '../../support/personas'
import { cacheNamespace } from '../../support/offline'

const INDEX = '**/api/**/gameplan.offline_downloads.get_offline_index'
const BUNDLE = '**/api/**/gameplan.offline_downloads.get_offline_bundle'

describe('Download for offline', () => {
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
    cy.intercept('POST', INDEX).as('index')
    cy.intercept('POST', BUNDLE).as('bundle')
  })

  /** The Offline section of Settings › Preferences, which is where a window is chosen. */
  const openOfflineSettings = () => {
    cy.visit('/g/settings/preferences')
    cy.contains('Download for offline', { timeout: 20000 }).scrollIntoView().should('be.visible')
  }

  const windowSelect = () =>
    cy
      .contains('Download for offline')
      .closest('div:has([role="combobox"])')
      .find('[role="combobox"]')

  /** A control in the Offline section, which sits below the fold of the settings dialog. */
  const control = (label: string) => cy.contains('button', label).scrollIntoView()

  const chooseWindow = (label: string) => {
    windowSelect().click()
    cy.contains('[role="option"]', label).click()
    cy.button('Download').click()
  }

  const startFreshDownload = () => {
    openOfflineSettings()
    // Cypress clears localStorage between tests, but IndexedDB download metadata survives.
    cachedValue('gameplan:offline-downloads', () => null)
    chooseWindow('Past week')
    cy.wait('@index')
    cy.contains('1 discussion downloaded', { timeout: 60000 }).should('be.visible')
  }

  const cachedValue = (key: string, change?: (value: any) => any) =>
    cy.window().then(
      (win) =>
        new Cypress.Promise<any>((resolve, reject) => {
          const opening = win.indexedDB.open('keyval-store')
          opening.onerror = () => reject(opening.error)
          opening.onsuccess = () => {
            const db = opening.result
            const transaction = db.transaction('keyval', change ? 'readwrite' : 'readonly')
            const store = transaction.objectStore('keyval')
            const request = store.get(key)
            request.onsuccess = () => {
              if (change) store.put(change(request.result), key)
            }
            transaction.oncomplete = () => {
              db.close()
              resolve(request.result)
            }
            transaction.onerror = () => {
              db.close()
              reject(transaction.error)
            }
          }
        }),
    )

  it('keeps the first index timestamp when the first download is interrupted', () => {
    cy.intercept('POST', BUNDLE, { statusCode: 500 }).as('failedBundle')
    openOfflineSettings()
    chooseWindow('Past week')
    cy.wait('@index').then(({ response }) => {
      cy.wait('@failedBundle')
      cy.contains('Could not finish the offline download').should('be.visible')
      cachedValue('gameplan:offline-downloads').then((meta) => {
        expect(meta.incomplete).to.eq(true)
        expect(meta.since).to.eq(response!.body.message.synced_at)
      })
    })
  })

  it('refreshes a legacy partial download that has no timestamp', () => {
    startFreshDownload()
    cachedValue('gameplan:offline-downloads', (meta) => ({
      ...meta,
      since: null,
      incomplete: true,
    }))
    cy.intercept({ method: 'POST', url: INDEX, times: 1 }, (req) =>
      req.continue((res) => {
        expect(req.body.since).to.eq(null)
        res.body.message.changed = []
      }),
    ).as('resumedIndex')
    cy.intercept('POST', BUNDLE, (req) =>
      req.continue((res) => {
        res.body.message.discussions[0].content = '<p>Edited during interruption</p>'
      }),
    ).as('resumedBundle')
    cy.intercept({ method: 'POST', url: BUNDLE, times: 1 }, { statusCode: 500 }).as(
      'interruptedResume',
    )
    control('Sync now').click()
    cy.button('Sync').click()
    cy.wait('@resumedIndex')
    cy.wait('@interruptedResume')
    cy.contains('Could not finish the offline download').should('be.visible')
    cachedValue('gameplan:offline-downloads').then((meta) => {
      expect(meta.places).to.deep.eq({})
      expect(meta.since).to.be.a('string')
    })
    control('Sync now').click()
    cy.button('Sync').click()
    cy.wait('@resumedBundle')
    control('Sync now').should('be.enabled')
    cachedValue(`${cacheNamespace(personas.member.email)}doc:v2:GP Discussion/${discussion}`).then(
      (value) => expect(JSON.parse(value).content).to.contain('Edited during interruption'),
    )
  })

  it('downloads the window and files it where the app already reads', () => {
    openOfflineSettings()
    chooseWindow('Past week')

    cy.wait('@index')
    cy.contains(/discussions? downloaded/, { timeout: 60000 }).should('be.visible')

    // Filed under the keys frappe-ui's own resources read, so a downloaded discussion
    // opens exactly like a visited one rather than through a second path.
    const namespace = cacheNamespace(personas.member.email)
    cy.idbKeys().should((keys) => {
      expect(keys, 'the discussion document').to.include(
        `${namespace}doc:v2:GP Discussion/${discussion}`,
      )
      const timelines = keys.filter(
        (key) =>
          key.startsWith(`${namespace}["useList:v2","Comments"`) &&
          key.includes(String(discussion)),
      )
      expect(timelines, 'its comment timeline').to.not.be.empty
    })
  })

  it('never files an answer given for another account', () => {
    // As if the cookie changed to another account while the request was in flight.
    cy.intercept('POST', BUNDLE, (req) =>
      req.continue((res) => {
        res.body.message.user = personas.secondMember.email
      }),
    ).as('bundle')
    openOfflineSettings()
    chooseWindow('Past week')
    cy.wait('@bundle')
    cy.contains('Could not finish the offline download').should('be.visible')

    cy.idbKeys().should((keys) => {
      const documents = keys.filter((key) => key.includes(`doc:v2:GP Discussion/${discussion}`))
      expect(documents, 'the discussion filed under any account').to.be.empty
    })
  })

  it('costs one index call when the device is already up to date', () => {
    openOfflineSettings()
    chooseWindow('Past week')
    cy.wait('@index')
    cy.contains(/discussions? downloaded/, { timeout: 60000 }).should('be.visible')

    cy.get('@bundle.all').then((first) => {
      const bundlesForFirstDownload = (first as unknown as unknown[]).length
      expect(bundlesForFirstDownload, 'a first download fetches at least one page').to.be.gte(1)

      // Nothing has changed since, so the second sync should ask the index and stop. The
      // server reports a minute of overlap to be safe, which here is everything just seeded.
      cy.intercept('POST', '**/gameplan.offline_downloads.get_offline_index', (req) =>
        req.continue((res) => {
          res.body.message.changed = []
        }),
      ).as('index')
      control('Sync now').click()
      cy.button('Sync').click()
      cy.wait('@index')
      cy.contains(/discussions? downloaded/, { timeout: 60000 }).should('be.visible')

      cy.get('@bundle.all').should((all) => {
        expect(
          (all as unknown as unknown[]).length,
          'no new bundle pages for an unchanged device',
        ).to.eq(bundlesForFirstDownload)
      })
    })
  })

  it('refreshes and clears reactions through the index without another bundle', () => {
    startFreshDownload()
    const reaction = {
      name: 'reaction',
      reference_doctype: 'GP Discussion',
      reference_name: discussion,
      emoji: '👍',
      user: personas.member.email,
    }
    const key =
      cacheNamespace(personas.member.email) +
      JSON.stringify(['useCall:v2', 'Thread Reactions', 'GP Discussion', discussion])
    cy.get('@bundle.all').then((first) => {
      const count = (first as unknown as unknown[]).length
      for (const reactions of [[reaction], []]) {
        cy.intercept({ method: 'POST', url: INDEX, times: 1 }, (req) =>
          req.continue((res) => {
            res.body.message.changed = []
            res.body.message.reactions[discussion] = reactions
          }),
        ).as('reactionIndex')
        control('Sync now').click()
        cy.button('Sync').click()
        cy.wait('@reactionIndex')
        control('Sync now').should('be.enabled')
        cachedValue(key).then((value) => expect(JSON.parse(value)).to.deep.eq(reactions))
        cy.get('@bundle.all').should((all) =>
          expect((all as unknown as unknown[]).length).to.eq(count),
        )
      }
    })
  })

  it('retries a failed image without fetching an unchanged bundle again', () => {
    const path = '/private/files/offline-image-retry.png'
    let fail = true
    cy.intercept('GET', path, (req) =>
      req.reply({ statusCode: fail ? 500 : 200, body: 'image' }),
    ).as('image')
    cy.intercept('POST', BUNDLE, (req) =>
      req.continue((res) => {
        res.body.message.discussions[0].content += `<img src="${path}">`
      }),
    ).as('bundle')
    openOfflineSettings()
    cy.window().should((win) => expect(win.navigator.serviceWorker.controller).to.exist)
    startFreshDownload()
    cy.wait('@image').its('response.statusCode').should('eq', 500)
    cy.get('@bundle.all').then((first) => {
      const count = (first as unknown as unknown[]).length
      cy.get('@index')
        .its('response.body.message')
        .then((index) => {
          cy.intercept('POST', INDEX, { body: { message: { ...index, changed: [] } } }).as(
            'unchanged',
          )
        })
      cy.then(() => (fail = false))
      control('Sync now').click()
      cy.button('Sync').click()
      cy.wait('@unchanged')
      cy.wait('@image').its('response.statusCode').should('eq', 200)
      control('Sync now').should('be.enabled')
      cy.get('@bundle.all').should((all) =>
        expect((all as unknown as unknown[]).length).to.eq(count),
      )
    })
  })

  it('opens a downloaded discussion offline that this browser never visited', () => {
    cy.request({
      method: 'POST',
      url: `/api/v2/document/GP%20Discussion/${discussion}/method/react`,
      body: { operations: [{ emoji: '👍', operation: 'add' }] },
    })
    cy.request({
      method: 'POST',
      url: '/api/v2/document/GP%20Comment',
      body: {
        reference_doctype: 'GP Discussion',
        reference_name: discussion,
        content: '<p>Downloaded reply</p>',
      },
    }).then(({ body }) => {
      cy.request({
        method: 'POST',
        url: `/api/v2/document/GP%20Comment/${body.data.name}/method/react`,
        body: { operations: [{ emoji: '💖', operation: 'add' }] },
      })
    })
    openOfflineSettings()
    chooseWindow('Past week')
    cy.wait('@index')
    cy.contains(/discussions? downloaded/, { timeout: 60000 }).should('be.visible')

    // The feed is fine to open online; the discussion itself never has been in this browser.
    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    cy.contains('a', 'Welcome thread').should('be.visible')
    cy.goOffline()
    cy.contains('a', 'Welcome thread').click()
    cy.contains('h1', 'Welcome thread').should('be.visible')
    cy.contains('button', /👍\s*1/).should('be.visible')
    cy.contains('Downloaded reply')
      .closest('[data-id]')
      .contains('button', /💖\s*1/)
      .should('be.visible')

    cy.goOnline()
  })

  it('removes a revoked download during the first sync after access is lost', () => {
    startFreshDownload()

    const feeds = ['Bookmarks', 'PersonPosts-profile', 'PersonReplies-profile']
    const retained = [
      { name: 'keep-last', title: 'Last' },
      { name: 'keep-first', title: 'First' },
    ]
    const key = (feed: string, user = personas.member.email) =>
      cacheNamespace(user) + JSON.stringify(['useList:v2', 'Discussions', feed])
    let database: IDBDatabase
    cy.window().then(
      (win) =>
        new Cypress.Promise<void>((resolve, reject) => {
          const opening = win.indexedDB.open('keyval-store')
          opening.onerror = () => reject(opening.error)
          opening.onsuccess = () => {
            database = opening.result
            const transaction = database.transaction('keyval', 'readwrite')
            const store = transaction.objectStore('keyval')
            const rows = [
              retained[0],
              {
                name: discussion,
                title: 'Revoked preview',
                content: 'Private body',
                last_comment_content: 'Private reply',
              },
              retained[1],
            ]
            for (const feed of feeds) store.put(JSON.stringify(rows), key(feed))
            store.put(JSON.stringify(rows), key('Bookmarks', personas.secondMember.email))
            transaction.oncomplete = () => resolve()
            transaction.onerror = () => reject(transaction.error)
          }
        }),
    )

    cy.intercept('POST', INDEX, (req) => {
      expect(req.body.cached, 'downloaded IDs are checked too').to.include(discussion)
      expect(req.body.cached.length, 'the access-check limit').to.be.at.most(2000)
      req.reply({
        body: {
          message: {
            user: personas.member.email,
            discussions: [],
            places: {},
            changed: [],
            revoked: [discussion],
            synced_at: new Date().toISOString(),
          },
        },
      })
    }).as('revokedIndex')
    control('Sync now').click()
    cy.button('Sync').click()
    cy.wait('@revokedIndex')
    cy.contains('0 discussions downloaded').should('be.visible')
    cy.then(
      () =>
        new Cypress.Promise<string[]>((resolve, reject) => {
          const transaction = database.transaction('keyval', 'readonly')
          const store = transaction.objectStore('keyval')
          const requests = [
            ...feeds.map((feed) => key(feed)),
            key('Bookmarks', personas.secondMember.email),
          ].map((cacheKey) => store.get(cacheKey))
          transaction.oncomplete = () => {
            database.close()
            resolve(requests.map((request) => request.result))
          }
          transaction.onerror = () => reject(transaction.error)
        }),
    ).then((stored) => {
      for (const rows of stored.slice(0, feeds.length))
        expect(JSON.parse(rows)).to.deep.eq(retained)
      expect(JSON.parse(stored[feeds.length])[1].title).to.eq('Revoked preview')
    })

    cy.idbKeys().should((keys) => {
      expect(keys).to.not.include(
        `${cacheNamespace(personas.member.email)}doc:v2:GP Discussion/${discussion}`,
      )
      expect(keys).to.not.include(
        cacheNamespace(personas.member.email) +
          JSON.stringify(['useCall:v2', 'Thread Reactions', 'GP Discussion', discussion]),
      )
    })
    cy.goOffline()
    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    cy.contains('No discussions').should('be.visible')
    cy.contains('a', 'Welcome thread').should('not.exist')
    cy.goOnline()
  })

  it('keeps a readable discussion that leaves the download window', () => {
    startFreshDownload()

    cy.intercept('POST', INDEX, {
      body: {
        message: {
          user: personas.member.email,
          discussions: [],
          places: {},
          changed: [],
          revoked: [],
          synced_at: new Date().toISOString(),
        },
      },
    }).as('agedIndex')
    control('Sync now').click()
    cy.button('Sync').click()
    cy.wait('@agedIndex')
    cy.contains('button', 'Remove downloads').should('not.exist')
    cy.idbKeys().should((keys) => {
      expect(keys).to.include(
        `${cacheNamespace(personas.member.email)}doc:v2:GP Discussion/${discussion}`,
      )
    })
  })

  it('removes the downloads and leaves nothing of them behind', () => {
    openOfflineSettings()
    chooseWindow('Past week')
    cy.wait('@index')
    cy.contains(/discussions? downloaded/, { timeout: 60000 }).should('be.visible')

    control('Remove downloads').click()
    cy.button('Remove').click()

    cy.idbKeys().should((keys) => {
      expect(keys, 'the downloaded document').to.not.include(
        `${cacheNamespace(personas.member.email)}doc:v2:GP Discussion/${discussion}`,
      )
      expect(keys, 'the downloaded reactions').to.not.include(
        cacheNamespace(personas.member.email) +
          JSON.stringify(['useCall:v2', 'Thread Reactions', 'GP Discussion', discussion]),
      )
      expect(keys, 'the record of what was downloaded').to.not.include('gameplan:offline-downloads')
    })
    cachedValue(
      cacheNamespace(personas.member.email) +
        JSON.stringify(['useList:v2', 'Discussions', `SpaceDiscussions-${space}`]),
    ).then((value) => expect(JSON.parse(value)).to.deep.eq([]))
    cy.goOffline()
    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    cy.contains('No discussions').should('be.visible')
    cy.contains('a', 'Welcome thread').should('not.exist')
    cy.goOnline()
  })

  it('keeps documents and feed rows fetched through normal browsing', () => {
    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    cy.contains('a', 'Welcome thread').click()
    cy.contains('h1', 'Welcome thread').should('be.visible')
    openOfflineSettings()
    chooseWindow('Past week')
    cy.wait('@index')
    cy.contains(/discussions? downloaded/, { timeout: 60000 }).should('be.visible')
    control('Remove downloads').click()
    cy.button('Remove').click()
    cy.contains('button', 'Remove downloads').should('not.exist')
    cy.idbKeys().should(
      'include',
      `${cacheNamespace(personas.member.email)}doc:v2:GP Discussion/${discussion}`,
    )
    cy.goOffline()
    cy.visit(`/g/community/${community}/space/${space}/discussions`)
    cy.contains('a', 'Welcome thread').should('be.visible')
    cy.contains('a', 'Welcome thread').click()
    cy.contains('h1', 'Welcome thread').should('be.visible')
    cy.goOnline()
  })

  it('says a download needs the connection before asking to confirm it', () => {
    openOfflineSettings()
    chooseWindow('Past week')
    cy.contains(/discussions? downloaded/, { timeout: 60000 }).should('be.visible')

    cy.goOffline()
    control('Sync now').click()
    cy.contains("You're offline. Reconnect to do this.").should('be.visible')
    cy.contains('Sync now?').should('not.exist')

    windowSelect().click()
    cy.contains('[role="option"]', 'Past month').click()
    cy.contains('Download for offline?').should('not.exist')
    windowSelect().should('contain.text', 'Past week')
  })
})
