import { resetData } from '../../support/seed'

it('does not render an old anonymous feed while checking current access', () => {
  resetData('public_space').then((ids) => {
    cy.clearCookies()
    cy.request({
      url: '/api/v2/method/gameplan.gameplan.doctype.gp_discussion.api.get_discussions',
      qs: { filters: JSON.stringify({ team: ids.community, feed_type: 'recent' }) },
    }).then(({ body }) => {
      const staleRows = body.data.map((row: object) => ({
        ...row,
        title: 'Old cached forum title',
      }))
      cy.visit('/login')
      cy.window().then(
        (win) =>
          new Cypress.Promise<void>((resolve, reject) => {
            const request = win.indexedDB.open('keyval-store')
            request.onupgradeneeded = () => request.result.createObjectStore('keyval')
            request.onerror = () => reject(request.error)
            request.onsuccess = () => {
              const db = request.result
              const transaction = db.transaction('keyval', 'readwrite')
              transaction
                .objectStore('keyval')
                .put(
                  JSON.stringify(staleRows),
                  JSON.stringify([
                    'useList:v2',
                    'Discussions',
                    `Discussions-${ids.community}-recent`,
                  ]),
                )
              transaction.oncomplete = () => {
                db.close()
                resolve()
              }
              transaction.onerror = () => reject(transaction.error)
            }
          }),
      )
      // Hold the fresh response long enough to expose an IndexedDB fallback.
      cy.intercept(
        'GET',
        '**/gameplan.gameplan.doctype.gp_discussion.api.get_discussions*',
        (req) => {
          req.continue((response) => response.setDelay(500))
        },
      ).as('feed')
      let showedOldTitle = false
      cy.visit(`/g/community/${ids.community}/discussions`, {
        onBeforeLoad(win) {
          new win.MutationObserver(() => {
            showedOldTitle ||=
              win.document.body?.textContent?.includes('Old cached forum title') ?? false
          }).observe(win.document, { childList: true, subtree: true })
        },
      })
      cy.wait('@feed')
      cy.contains('Welcome to Open Source').should('be.visible')
      cy.then(() => expect(showedOldTitle, 'old anonymous feed was displayed').to.eq(false))
    })
  })
})
