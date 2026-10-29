import { resetData, type SeedIds } from '../../support/seed'

describe('Public forum search', () => {
  let ids: SeedIds

  beforeEach(() => {
    resetData('public_space').then((seeded) => {
      ids = seeded
      cy.request('POST', '/api/method/gameplan.ui_test_helpers.rebuild_search_index')
    })
    cy.clearCookies()
  })

  it('reuses Search and exposes only public types, spaces, and safe author metadata', () => {
    cy.intercept('GET', '**/gameplan.api.search_sqlite*').as('search')
    cy.visit('/g/search?q=Welcome')
    cy.wait('@search').then(({ response }) => {
      expect(response?.statusCode).to.eq(200)
      expect(response?.body.data.results).to.have.length(1)
      expect(JSON.stringify(response?.body)).not.to.include('@example.com')
    })
    cy.contains('a', 'Welcome to Open Source').should('be.visible')
    cy.contains('button', 'Author').should('not.exist')
    cy.contains('button', 'Tags').should('not.exist')
    cy.contains('Helpful?').should('not.exist')
    cy.contains('button', 'Type').click()
    cy.contains('[role="option"]', 'Discussion').should('be.visible')
    cy.contains('[role="option"]', 'Task').should('not.exist')
    cy.contains('[role="option"]', 'Page').should('not.exist')
    cy.get('body').type('{esc}')
    cy.contains('a', 'Welcome to Open Source').click()
    cy.location('pathname').should('include', `/discussion/${ids.discussion}`)
  })

  it('lets a mobile visitor find a reply and open its public thread', () => {
    cy.viewport(390, 844)
    cy.visit(`/g/community/${ids.community}/discussions`)
    cy.get('header:visible [aria-label="Search"]').click()
    cy.location('pathname').should('eq', '/g/search')
    cy.get('header:visible').button('Log in').should('be.visible')
    cy.get('input[aria-label="Search"]').type('Glad{enter}')
    cy.contains('a', 'Glad to be here.').should('be.visible').click()
    cy.location('pathname').should('include', `/discussion/${ids.discussion}`)
    cy.location('search').should('include', 'comment=')
    cy.contains('Join the conversation').scrollIntoView().should('be.visible')
  })

  it('checks permissions again on reload instead of restoring cached public results', () => {
    cy.visit('/g/search?q=Welcome')
    cy.contains('a', 'Welcome to Open Source').should('be.visible')
    cy.task('requestAsUser', {
      user: 'Administrator',
      path: `/api/v2/document/GP Project/${ids.space}/method/set_visibility`,
      body: { visibility: 'General' },
    })
    cy.reload()
    cy.contains('a', 'Welcome to Open Source').should('not.exist')
    cy.contains('0 matches').should('be.visible')
  })

  it('opens later replies through search and keeps their embedded polls on the same page', () => {
    const draft = JSON.stringify({
      title: 'Question in the later reply',
      options: [{ title: 'Yes' }, { title: 'No' }],
    }).replaceAll('"', '&quot;')
    cy.login()
    cy.then(() =>
      cy.request({
        method: 'POST',
        url: '/api/method/frappe.client.insert_many',
        body: {
          docs: Array.from({ length: 50 }, (_, i) => ({
            doctype: 'GP Comment',
            reference_doctype: 'GP Discussion',
            reference_name: ids.discussion,
            content:
              i === 49
                ? `<p>Borealreply</p><div data-type="poll" data-poll-draft="${draft}"></div>`
                : `<p>Earlier reply ${i + 1}</p>`,
          })),
        },
      }),
    )
    cy.request('POST', '/api/method/gameplan.ui_test_helpers.rebuild_search_index')
    cy.clearCookies()
    cy.visit(
      `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`,
    )
    cy.contains('Question in the later reply').should('not.exist')
    cy.contains('a', 'Next page of replies').click()
    cy.contains('Question in the later reply').should('be.visible')
    cy.contains('Poll unavailable').should('not.exist')
    cy.visit('/g/search?q=Borealreply')
    cy.contains('a', 'Borealreply').click()
    cy.location('search').should('include', 'page=2').and('include', 'comment=')
    cy.contains('Borealreply').should('be.visible')
    cy.contains('Question in the later reply').should('be.visible')
    cy.contains('Poll unavailable').should('not.exist')
    cy.request(
      `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}?page=2`,
    )
      .its('body')
      .should('include', 'Question in the later reply')
    cy.location('search', { timeout: 15000 }).should('eq', '?page=2')
  })

  it('refuses author probing and cannot search a non-public space', () => {
    cy.request({
      url: '/api/method/gameplan.api.search_sqlite',
      qs: { query: 'Welcome', filters: JSON.stringify({ owner: ['member@example.com'] }) },
      failOnStatusCode: false,
    })
      .its('status')
      .should('eq', 403)
    cy.request({
      url: '/api/method/gameplan.api.search_sqlite',
      qs: { query: 'thread', filters: JSON.stringify({ project: [String(ids.private_space)] }) },
    })
      .its('body.message.results')
      .should('deep.equal', [])
  })
})
