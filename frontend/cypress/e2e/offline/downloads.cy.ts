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

  it('opens a downloaded discussion offline that this browser never visited', () => {
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

    cy.goOnline()
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
      expect(keys, 'the record of what was downloaded').to.not.include('gameplan:offline-downloads')
    })
  })

  it('leaves the window alone while offline, where nothing could be fetched', () => {
    openOfflineSettings()

    cy.goOffline()
    windowSelect().should('be.disabled')

    cy.goOnline()
  })
})
