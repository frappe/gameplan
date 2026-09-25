// The app shell: a reload while offline opens the app from the service worker's cache
// instead of the browser's error page, and a new build offers a refresh rather than
// swapping the code under whoever is reading.
//
// A worker only registers in a secure context, and in a dev build it is skipped entirely
// (offline.ts's `serviceWorkerSupportEnabled`). Both are stated up front so a run that
// cannot exercise it fails loudly rather than passing on a technicality.
import { resetData } from '../../support/seed'
import { CACHE_PREFIX, secureOrigin } from '../../support/offline'

describe('App shell offline', () => {
  before(() => {
    if (!secureOrigin()) {
      throw new Error(
        `A service worker cannot register on ${Cypress.config('baseUrl')}: it needs a secure ` +
          `origin, which over http means localhost or a loopback address. Serve the site pinned ` +
          `(bench --site <site> serve) or as the default site, reach it on localhost, and set ` +
          `GAMEPLAN_SITE=<site> — as .github/workflows/ui-test.yml does.`,
      )
    }
  })

  beforeEach(() => {
    resetData('space_with_discussion')
    cy.loginAs('member')
  })

  /** Waits for the worker to control the page, which is when it can serve the shell. */
  const workerReady = () =>
    cy.window({ timeout: 40000 }).should((win) => {
      expect(win.navigator.serviceWorker, 'service worker API').to.exist
      expect(win.navigator.serviceWorker.controller, 'a worker controls the page').to.exist
    })

  it('serves the app from cache when reloaded offline', () => {
    cy.visit('/g')
    cy.get('[data-slot="desktop-shell"]').should('exist')
    workerReady()

    cy.cacheNames().should((names) => {
      expect(names.filter((n) => n.startsWith(CACHE_PREFIX))).to.not.be.empty
    })

    cy.goOffline()
    cy.reload()
    // The shell is what the worker holds: the app boots, rather than the browser's
    // "no internet" page. What it can then render is reading.cy.ts's business.
    cy.get('#app', { timeout: 40000 }).should('exist')
    cy.contains('[role="status"]', 'Offline').should('be.visible')

    cy.goOnline()
  })

  it('offers a refresh when a new build is waiting', () => {
    // A new deploy is a byte-different worker script at the same URL. Serving one is all
    // it takes for the browser to install it and park it in `waiting`, which is the state
    // the page's update watcher is meant to notice.
    cy.intercept('GET', '/gameplan-sw.js', (req) => {
      req.continue((res) => {
        res.body = `${res.body}\n// forced update ${Date.now()}\n`
      })
    }).as('workerScript')

    cy.visit('/g')
    workerReady()

    cy.window()
      .then((win) => win.navigator.serviceWorker.getRegistration('/g'))
      .then((registration) => {
        expect(registration, 'registration for the /g scope').to.exist
        return registration!.update()
      })

    cy.contains('A new version of Gameplan is available', { timeout: 40000 }).should('be.visible')
    cy.button('Refresh').should('be.visible')
  })
})
